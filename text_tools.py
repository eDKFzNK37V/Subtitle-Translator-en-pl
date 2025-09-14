from typing import List, Tuple
import re
from functools import lru_cache
import torch
from config import DEVICE
from models import PUNCT_MODELS, PUNCT_TOKENIZERS, GRAMMAR_MODEL, GRAMMAR_TOKENIZER

def correct_punctuation(text, model_choice="kredor"):
    model = PUNCT_MODELS[model_choice]
    tokenizer = PUNCT_TOKENIZERS[model_choice]
    tokens = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(DEVICE)
    with torch.no_grad():
        logits = model(**tokens).logits
        preds = torch.argmax(logits, dim=2)[0]
    input_ids = tokens["input_ids"][0]
    labels = model.config.id2label

    corrected_words = []
    current_word = ""
    for token_id, pred_id in zip(input_ids, preds):
        token = tokenizer.convert_ids_to_tokens(token_id.item())
        label = labels[pred_id.item()]
        if token in ["<s>", "</s>", "<pad>", "<unk>"]:
            continue
        if token.startswith("▁"):
            if current_word:
                corrected_words.append(current_word)
            current_word = token[1:]
        else:
            current_word += token
        if label != "O":
            punct_map = {"LABEL_COMMA": ",", "LABEL_PERIOD": ".", "LABEL_QUESTION": "?"}
            current_word += punct_map.get(label, "")
    if current_word:
        corrected_words.append(current_word)
    return " ".join(corrected_words)

def correct_grammar(text):
    """
    Optimized grammar correction with confidence scoring for performance.
    """
    try:
        inputs = GRAMMAR_TOKENIZER.encode("gec: " + text, return_tensors="pt", max_length=200, truncation=True).to(DEVICE)
        with torch.no_grad():
            outputs = GRAMMAR_MODEL.generate(
                inputs, 
                max_length=200,  # Reduced for performance
                num_beams=3,     # Reduced for speed
                early_stopping=True,
                output_scores=True,
                return_dict_in_generate=True,
                no_repeat_ngram_size=2
            )
        
        corrected = GRAMMAR_TOKENIZER.decode(outputs.sequences[0], skip_special_tokens=True)
        
        # Quick confidence calculation for performance
        if abs(len(text) - len(corrected)) / max(len(text), 1) < 0.3:
            confidence = 1.0 - abs(len(text) - len(corrected)) / max(len(text), len(corrected))
        else:
            confidence = 0.4  # Low confidence for significant changes
            
        return corrected, confidence
    except Exception:
        return text, 0.0

def calculate_text_similarity_confidence(original: str, corrected: str) -> float:
    """
    Calculate confidence based on text similarity and correction magnitude.
    """
    if original == corrected:
        return 1.0
    
    # Simple character-level similarity
    len_diff = abs(len(original) - len(corrected))
    max_len = max(len(original), len(corrected))
    
    if max_len == 0:
        return 1.0
    
    # Penalize large changes more heavily
    length_ratio = 1.0 - (len_diff / max_len)
    
    # Count character matches
    matches = sum(1 for a, b in zip(original.lower(), corrected.lower()) if a == b)
    char_ratio = matches / max_len if max_len > 0 else 1.0
    
    # Combine metrics
    confidence = (length_ratio * 0.3 + char_ratio * 0.7)
    return max(0.0, min(1.0, confidence))

def correct_grammar_with_fallback(text: str, confidence_threshold: float = 0.75) -> str:
    """
    Conservative grammar correction with enhanced Polish character protection.
    Enhanced confidence-based fallback to prevent over-correction.
    """
    # Safety check for Polish characters - be extra conservative
    polish_chars = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż', 'Ą', 'Ć', 'Ę', 'Ł', 'Ń', 'Ó', 'Ś', 'Ź', 'Ż']
    has_polish_chars = any(char in text for char in polish_chars)
    
    # Use higher confidence threshold for Polish text to prevent character loss
    effective_threshold = confidence_threshold + 0.1 if has_polish_chars else confidence_threshold
    
    corrected, confidence = correct_grammar(text)
    
    # Additional safety check: if Polish characters are lost, reject correction
    if has_polish_chars:
        corrected_has_polish = any(char in corrected for char in polish_chars)
        if not corrected_has_polish and any(char in text for char in polish_chars):
            return text  # Return original if Polish characters were lost
    
    if confidence >= effective_threshold:
        return corrected
    else:
        return text

def clean_translation(text):
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

# Legacy helpers (kept for compatibility; these move tags to the front)
def extract_tags(text):
    # Only extract {\...} tags, not \N or similar linebreaks
    tags = re.findall(r"{\\.*?}", text)
    clean_text = re.sub(r"{\\.*?}", "", text)
    return clean_text, tags

TAG_ONLY = re.compile(r"({\\.*?})")

def group_dialogue_lines(lines: List[str]) -> Tuple[List[str], List[List[int]]]:
    """
    Groups consecutive lines for translation if the next line starts with a lowercase letter.
    Enhanced to preserve idioms and context better.
    
    Improvements:
    - Detects common idioms and phrases that shouldn't be split
    - Considers punctuation context for better grouping decisions
    - Preserves dialogue flow while avoiding over-grouping
    
    Returns:
        grouped_lines: List of joined lines for translation
        mapping: List of lists, each sublist contains the original line indices for each group
    """
    # Essential patterns for performance (reduced set)
    IDIOM_PATTERNS = [
        r'\b(in order to|as well as|not only|but also)\b',
        r'\b(on the other hand|at the same time)\b',
    ]
    
    # Streamlined patterns for better performance
    CONTINUATION_PATTERNS = [
        r'^(and|but|or|so|then)\s',  # Most common connectors
        r'^[a-z]',  # lowercase start (original logic)
    ]
    
    # Essential break patterns
    BREAK_PATTERNS = [
        r'[.!?]\s*$',  # ends with sentence-ending punctuation
        r':\s*$',      # ends with colon
    ]
    
    def should_continue_group(prev_line: str, curr_line: str) -> bool:
        """
        Optimized determination if current line should continue the previous group.
        """
        if not curr_line.strip():
            return False
        
        curr_lower = curr_line.lower()
        prev_ends_with_punct = prev_line.rstrip()[-1:] in '.!?:'
        
        # Check for common continuation patterns first (most frequent)
        if curr_lower.startswith(('and ', 'but ', 'or ', 'so ', 'then ')):
            return not prev_ends_with_punct
        
        # Check for lowercase start (original logic)
        if curr_line[0].islower():
            return not prev_ends_with_punct
        
        # Quick idiom check (simplified)
        combined = (prev_line + " " + curr_line).lower()
        if any(phrase in combined for phrase in ['in order to', 'as well as', 'not only', 'but also']):
            return True
                
        return False
    
    def is_natural_break(line: str) -> bool:
        """
        Quick check if a line naturally ends a thought/sentence.
        """
        return line.rstrip()[-1:] in '.!?:'
    
    grouped_lines = []
    mapping = []
    i = 0
    
    while i < len(lines):
        group = [lines[i]]
        indices = [i]
        
        # Look ahead to group continuation lines
        while i + 1 < len(lines):
            next_line = lines[i + 1]
            current_line = lines[i]
            
            # Don't group if we've reached maximum reasonable group size
            if len(group) >= 3:
                break
                
            # Check if next line should continue this group
            if should_continue_group(current_line, next_line):
                group.append(next_line)
                indices.append(i + 1)
                i += 1
            else:
                break
        
        # Join group with appropriate spacing
        if len(group) == 1:
            grouped_text = group[0]
        else:
            # Use smart joining - preserve natural sentence flow
            joined_parts = []
            for j, part in enumerate(group):
                if j == 0:
                    joined_parts.append(part)
                else:
                    # Add appropriate connector
                    prev_part = group[j-1]
                    if is_natural_break(prev_part):
                        joined_parts.append(" " + part)
                    else:
                        joined_parts.append(" " + part)
            grouped_text = "".join(joined_parts)
        
        grouped_lines.append(grouped_text)
        mapping.append(indices)
        i += 1
    
    return grouped_lines, mapping

def split_grouped_translations(translated_groups: List[str], mapping: List[List[int]]) -> List[str]:
    """
    Splits translated grouped lines back into the original number of lines.
    Each group is split into len(indices) lines using simple sentence splitting (by period/question/exclamation or evenly if not enough sentences).
    """
    import re
    result = []
    for group_text, indices in zip(translated_groups, mapping):
        # Try to split by sentence-ending punctuation
        sentences = re.split(r'(?<=[.!?])\s+', group_text.strip())
        # If not enough sentences, split by space
        if len(sentences) < len(indices):
            words = group_text.strip().split()
            chunk_size = max(1, len(words) // len(indices))
            sentences = [" ".join(words[i*chunk_size:(i+1)*chunk_size]) for i in range(len(indices))]
        # Pad or trim to match number of lines
        while len(sentences) < len(indices):
            sentences.append("")
        for idx in range(len(indices)):
            result.append(sentences[idx].strip())
    return result


def extract_newline_tags(text: str) -> Tuple[str, int]:
    r"""
    Remove all \N (and variants) from text, return cleaned text and count of tags.
    """
    # Replace \N with a single space to preserve separation
    cleaned = re.sub(r"\\[Nn]", " ", text)
    count = len(re.findall(r"\\[Nn]", text))
    return cleaned, count

def insert_newline_tags_at_wordidx(text: str, n_tags: int, word_idx: int) -> str:
    r"""
    Insert n_tags of \N at the specified word index (after the word at that index).
    If word_idx >= number of words, append at end.
    """
    words = re.findall(r'\S+|\s+', text)
    # Find word boundaries (skip whitespace tokens)
    word_positions = [i for i, w in enumerate(words) if not w.isspace()]
    if not word_positions:
        # No words, just return tags
        return ("\\N" * n_tags) + text
    # Find insertion point
    if word_idx < 0:
        insert_at = 0
    elif word_idx >= len(word_positions):
        insert_at = len(words)
    else:
        insert_at = word_positions[word_idx] + 1
    # Insert tags
    tag_str = "\\N" * n_tags
    new_words = words[:insert_at] + [tag_str] + words[insert_at:]
    return ''.join(new_words)

def insert_newline_tags_contextaware(text: str, n_tags: int, prefer_punctuation: bool = True) -> str:
    r"""
    Context-aware insertion of \N tags using punctuation and clause boundaries.
    
    Args:
        text: The text to insert tags into
        n_tags: Number of \N tags to insert
        prefer_punctuation: If True, prefer insertion after punctuation marks
    
    Returns:
        Text with \N tags inserted at natural breaking points
    """
    if n_tags <= 0 or not text.strip():
        return text
    
    # Find potential insertion points
    insertion_points = []
    
    # Look for punctuation-based breaks (highest priority)
    if prefer_punctuation:
        for match in re.finditer(r'[.!?,:;]\s+', text):
            insertion_points.append((match.end(), 'punctuation', 3))
    
    # Look for clause boundaries with conjunctions
    for match in re.finditer(r'\b(and|but|or|so|yet|for|nor|because|since|although|while|if|when|where|after|before)\s+', text, re.IGNORECASE):
        insertion_points.append((match.start(), 'conjunction', 2))
    
    # Look for natural pauses (commas, dashes)
    for match in re.finditer(r'[,—–-]\s+', text):
        insertion_points.append((match.end(), 'pause', 1))
    
    # If no good punctuation found, use word boundaries
    if not insertion_points:
        words = [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]
        if words:
            # Insert roughly in the middle, favoring natural breaks
            mid_point = len(words) // 2
            if mid_point < len(words):
                insertion_points.append((words[mid_point][0], 'word', 0))
    
    # Sort by priority (higher priority first), then by position
    insertion_points.sort(key=lambda x: (-x[2], x[0]))
    
    # Insert tags at best positions
    result = text
    tags_inserted = 0
    offset = 0
    
    for pos, point_type, priority in insertion_points:
        if tags_inserted >= n_tags:
            break
            
        # Adjust position for previous insertions
        adjusted_pos = pos + offset
        
        # Insert one \N tag
        result = result[:adjusted_pos] + "\\N" + result[adjusted_pos:]
        offset += 2  # Length of "\\N"
        tags_inserted += 1
    
    # If we still need more tags, append remaining at the end
    while tags_inserted < n_tags:
        result += "\\N"
        tags_inserted += 1
    
    return result

def restore_tags(translated, tags):
    return "".join(tags) + translated

def correct_text_pipeline(text, lang):
    text = correct_grammar(text)
    text = correct_punctuation(text)
    return clean_translation(text)

# Optional: strip all tags and escapes permanently
def strip_subtitle_tags(text: str) -> str:
    text = re.sub(r"{\\[^}]+}", "", text)
    text = re.sub(r"\\[NnHhRr]", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

# ------------------------------------------------------------------------
# Placeholder-based tag handling (exact position preservation)
# ------------------------------------------------------------------------

    # Only match {\...} tags, not \N or similar linebreaks
TAG_ONLY = re.compile(r"({\\.*?})")

import re
from typing import List, Tuple

TAG_OR_ESCAPE = re.compile(r"({\\.*?})|(\\[NnHhRr])")

def extract_tags_with_placeholders(text: str) -> Tuple[str, List[Tuple[str, str, int]]]:
    """
    Replace all tags/escapes with unique placeholders and return:
      clean_text, ph_map
    ph_map: list of tuples (placeholder, original_value, original_pos)
    """
    ph_map = []
    idx = 0

    def repl(m):
        nonlocal idx
        placeholder = f"<TAGPH_{idx}>"
        ph_map.append((placeholder, m.group(0), m.start()))
        idx += 1
        return placeholder

    # Use re.sub to directly replace tags/escapes with placeholders, preserving all other text
    clean_text = TAG_ONLY.sub(repl, text)
    return clean_text, ph_map

def restore_tags_from_placeholders(translated: str, ph_map: List[Tuple[str, str, int]]) -> str:
    """
    Replace placeholders in translated text with original tags/escapes.
    If a placeholder is missing (model dropped it), insert the tag at the
    closest possible position based on semantic similarity and word boundaries.
    
    Improvements:
    - Better word boundary detection
    - Semantic positioning based on relative word positions
    - Improved spacing logic to prevent tag-word collisions
    """
    out = translated

    # First pass: replace placeholders that survived translation
    for placeholder, original, _pos in ph_map:
        if placeholder in out:
            out = out.replace(placeholder, original)

    # Second pass: insert any missing tags at their approximate original positions
    # Sort by original position so earlier inserts don't break later positions too badly
    missing = [(p, o, pos) for (p, o, pos) in ph_map if p not in translated]
    missing.sort(key=lambda x: x[2])

    def find_optimal_insertion_point(text: str, original_pos: int, original_total_len: int) -> int:
        """
        Find the best insertion point using relative positioning and word boundaries.
        """
        if not text.strip():
            return 0
            
        # Calculate relative position (0.0 to 1.0)
        relative_pos = original_pos / max(original_total_len, 1)
        target_char = int(relative_pos * len(text))
        
        # Find nearest word boundary
        words = [(m.group(), m.start(), m.end()) for m in re.finditer(r'\S+', text)]
        if not words:
            return 0
            
        # Find the word closest to our target position
        best_insert = 0
        min_distance = float('inf')
        
        for i, (word, start, end) in enumerate(words):
            # Check both before and after this word
            distances = [
                (abs(start - target_char), start),  # before word
                (abs(end - target_char), end)       # after word
            ]
            
            for distance, pos in distances:
                if distance < min_distance:
                    min_distance = distance
                    best_insert = pos
        
        return best_insert

    def insert_tag_with_smart_spacing(text: str, pos: int, tag: str) -> str:
        """
        Insert tag with intelligent spacing to avoid collisions.
        """
        if pos <= 0:
            # Insert at beginning
            if text and text[0].isalnum():
                return tag + ' ' + text
            return tag + text
        elif pos >= len(text):
            # Insert at end  
            if text and text[-1].isalnum():
                return text + ' ' + tag
            return text + tag
        else:
            # Insert in middle
            before_char = text[pos-1] if pos > 0 else ' '
            after_char = text[pos] if pos < len(text) else ' '
            
            space_before = ' ' if before_char.isalnum() else ''
            space_after = ' ' if after_char.isalnum() else ''
            
            return text[:pos] + space_before + tag + space_after + text[pos:]

    # Get original text length for relative positioning
    original_total_len = max([pos for _, _, pos in ph_map] + [len(translated)]) if ph_map else len(translated)
    
    for _placeholder, original, pos in missing:
        insert_at = find_optimal_insertion_point(out, pos, original_total_len)
        out = insert_tag_with_smart_spacing(out, insert_at, original)

    return out


def correct_grammar_batch(texts, confidence_threshold: float = 0.65):
    """
    Optimized batched grammar correction with confidence-based fallback.
    Enhanced for performance while maintaining quality.
    """
    try:
        inputs = GRAMMAR_TOKENIZER(
            ["gec: " + t for t in texts],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=200  # Reduced for better performance
        ).to(DEVICE)
        
        with torch.no_grad():
            outputs = GRAMMAR_MODEL.generate(
                inputs.input_ids, 
                attention_mask=inputs.attention_mask,
                max_length=200,  # Reduced for performance
                num_beams=3,     # Reduced for speed while maintaining quality
                early_stopping=True,
                output_scores=True,
                return_dict_in_generate=True,
                no_repeat_ngram_size=2  # Added to reduce repetition
            )
        
        corrected_texts = GRAMMAR_TOKENIZER.batch_decode(outputs.sequences, skip_special_tokens=True)
        
        # Apply confidence-based fallback for each text efficiently
        results = []
        for i, (original, corrected) in enumerate(zip(texts, corrected_texts)):
            # Quick confidence check with optimized calculation
            if len(corrected) > 0 and abs(len(original) - len(corrected)) / max(len(original), 1) < 0.3:
                # Length-based quick confidence for performance
                confidence = 1.0 - abs(len(original) - len(corrected)) / max(len(original), len(corrected))
                if confidence >= confidence_threshold:
                    results.append(corrected)
                    continue
            results.append(original)
        
        return results
    except Exception:
        return texts

def correct_punctuation_batch(texts, model_choice="kredor"):
    """
    Batched punctuation restoration for a list of strings.
    """
    try:
        model = PUNCT_MODELS[model_choice]
        tok = PUNCT_TOKENIZERS[model_choice]
        enc = tok(texts, return_tensors="pt", truncation=True, padding=True).to(DEVICE)
        with torch.no_grad():
            logits = model(**enc).logits  # [B, T, C]
            preds = torch.argmax(logits, dim=2)  # [B, T]
        labels = model.config.id2label
        input_ids = enc["input_ids"]  # [B, T]

        def decode_one(ids_row, preds_row):
            words, cur = [], ""
            for token_id, pred_id in zip(ids_row.tolist(), preds_row.tolist()):
                token = tok.convert_ids_to_tokens(token_id)
                label = labels.get(pred_id, "O")
                if token in ["<s>", "</s>", "<pad>", "<unk>"]:
                    continue
                if token.startswith("▁"):
                    if cur:
                        words.append(cur)
                    cur = token[1:]
                else:
                    cur += token
                if label != "O":
                    punct_map = {"LABEL_COMMA": ",", "LABEL_PERIOD": ".", "LABEL_QUESTION": "?"}
                    cur += punct_map.get(label, "")
            if cur:
                words.append(cur)
            return " ".join(words)

        return [decode_one(ids_row, pred_row) for ids_row, pred_row in zip(input_ids, preds)]
    except Exception:
        return texts

def adjust_subtitle_style_tone(text: str, target_lang: str = "pl") -> str:
    """
    Enhanced subtitle style and tone adjustment with comprehensive pattern detection.
    
    Subtitle-specific adjustments:
    - Shorter, more concise phrasing
    - More natural, conversational tone
    - Removal of overly formal language
    - Cultural adaptation for target language
    - Advanced awkward construction detection
    """
    if not text.strip():
        return text
    
    # Define style adjustments for different languages
    if target_lang.lower() == "pl":
        # Comprehensive Polish subtitle style adjustments
        adjustments = [
            # Remove overly formal constructions
            (r'\bchciałbym\s+powiedzieć,?\s*że\b', 'chcę powiedzieć, że'),
            (r'\bmuszę\s+przyznać,?\s*że\b', 'przyznaję, że'),
            (r'\bbyłbym\s+bardzo\s+wdzięczny\b', 'bardzo by mi to pomogło'),
            (r'\bwydaje\s+mi\s+się,?\s*że\b', 'myślę, że'),
            (r'\bobawiam\s+się,?\s*że\b', 'niestety'),
            (r'\bbyć\s+może\s+powinniśmy\b', 'może powinniśmy'),
            (r'\bpragnę\s+aby\b', 'chcę żeby'),
            (r'\bżyczę\s+sobie\b', 'chcę'),
            (r'\bmam\s+zamiar\b', 'zamierzam'),
            (r'\bpozwolę\s+sobie\b', 'pozwolę'),
            
            # Enhanced awkward construction fixes
            (r'\bw\s+tym\s+momencie\s+jestem\b', 'teraz jestem'),
            (r'\bw\s+chwili\s+obecnej\s+znajduję\s+się\b', 'teraz jestem'),
            (r'\baktualnie\s+wykonuję\s+czynność\b', 'robię'),
            (r'\bobecnie\s+zajmuję\s+się\b', 'zajmuję się'),
            (r'\bw\s+tej\s+chwili\s+mam\s+do\s+czynienia\b', 'mam do czynienia'),
            
            # Simplify complex phrases
            (r'\bw\s+związku\s+z\s+tym\b', 'dlatego'),
            (r'\bw\s+rezultacie\b', 'w wyniku'),
            (r'\bw\s+konsekwencji\b', 'przez to'),
            (r'\bw\s+celu\s+ukończenia\b', 'żeby ukończyć'),
            (r'\bw\s+celu\s+([a-ząćęłńóśźż\s]+)\b', r'żeby \1'),
            (r'\bz\s+powodu\s+tego,?\s*że\b', 'bo'),
            (r'\bna\s+skutek\s+tego\b', 'przez to'),
            (r'\bz\s+uwagi\s+na\s+to,?\s*że\b', 'bo'),
            (r'\bjeśli\s+chodzi\s+o\b', 'co do'),
            (r'\bw\s+odniesieniu\s+do\b', 'co do'),
            (r'\bw\s+kontekście\b', 'co do'),
            
            # Make more natural for speech
            (r'\bale\s+jednak\b', 'ale'),
            (r'\bjednak\s+jednak\b', 'jednak'),
            (r'\bprawda\s+jest\s+taka,?\s*że\b', 'prawda jest, że'),
            (r'\bproduktów\s+spożywczych\b', 'jedzenia'),
            (r'\bartykułów\s+żywnościowych\b', 'jedzenia'),
            (r'\bśrodków\s+czystości\b', 'detergentów'),
            
            # Enhanced conversational replacements
            (r'\bna\s+pewno\b', 'pewnie'),
            (r'\bprawdopodobnie\b', 'pewnie'),
            (r'\bzupełnie\s+nie\b', 'wcale nie'),
            (r'\bbardzo\s+dziękuję\b', 'dzięki'),
            (r'\bdzięki\s+bardzo\b', 'dzięki'),
            (r'\bjestem\s+wdzięczny\b', 'dzięki'),
            (r'\bjest\s+mi\s+bardzo\s+miło\b', 'miło mi'),
            
            # Time expression improvements
            (r'\bw\s+najbliższym\s+czasie\b', 'niedługo'),
            (r'\bw\s+przyszłości\b', 'później'),
            (r'\bw\s+przeszłości\b', 'wcześniej'),
            (r'\bobecnie\b', 'teraz'),
            (r'\baktualnie\b', 'teraz'),
            (r'\bw\s+tym\s+momencie\b', 'teraz'),
            
            # Verb form simplifications
            (r'\bzostanie\s+wykonane\b', 'zrobimy to'),
            (r'\bbędzie\s+realizowane\b', 'zrobimy'),
            (r'\buzostanie\s+ukończone\b', 'ukończymy'),
            (r'\bmieć\s+miejsce\b', 'się wydarzyć'),
            (r'\bodbywa\s+się\b', 'dzieje się'),
            (r'\bdokonuje\s+się\b', 'dzieje się'),
        ]
    else:
        # Enhanced English subtitle style adjustments
        adjustments = [
            # Enhanced contractions
            (r"\bI am\b(?!\s+going\s+to)", "I'm"),
            (r"\byou are\b", "you're"),
            (r"\bwe are\b", "we're"),
            (r"\bthey are\b", "they're"),
            (r"\bhe is\b", "he's"),
            (r"\bshe is\b", "she's"),
            (r"\bit is\b(?!\s+important)", "it's"),
            (r"\bthere is\b", "there's"),
            (r"\bthat is\b", "that's"),
            (r"\bwould have\b", "would've"),
            (r"\bcould have\b", "could've"),
            (r"\bshould have\b", "should've"),
            (r"\bmight have\b", "might've"),
            (r"\bmust have\b", "must've"),
            
            # Convert formal expressions to conversational
            (r"\bI would like to\b", "I'd like to"),
            (r"\bI would be very grateful if\b", "I'd really appreciate if"),
            (r"\bIt is important that\b", "You need to"),
            (r"\bI am afraid that\b", "I'm afraid"),
            (r"\bPerhaps we should\b", "Maybe we should"),
            (r"\bIt seems to me that\b", "I think"),
            (r"\bI would suggest that\b", "I think"),
            (r"\bI would recommend that\b", "I'd say"),
            (r"\bI believe it would be best if\b", "I think you should"),
            
            # Enhanced awkward construction fixes
            (r"\bAt this point in time I am\b", "I'm now"),
            (r"\bIn this moment I find myself\b", "I'm now"),
            (r"\bCurrently I am engaged in\b", "I'm doing"),
            (r"\bPresently I am involved in\b", "I'm doing"),
            (r"\bAt the present time I have\b", "I now have"),
            
            # Make more conversational
            (r"\bI'm going to\b", "I'll"),
            (r"\bdo not\b", "don't"),
            (r"\bcannot\b", "can't"),
            (r"\bwill not\b", "won't"),
            (r"\bshall not\b", "won't"),
            (r"\bmust not\b", "can't"),
            (r"\bshould not\b", "shouldn't"),
            (r"\bwould not\b", "wouldn't"),
            (r"\bcould not\b", "couldn't"),
            (r"\bmight not\b", "might not"),
            
            # Remove unnecessary filler
            (r'\bwell,?\s+', ''),
            (r'\buh,?\s+', ''),
            (r'\bum,?\s+', ''),
            (r'\byou know,?\s+', ''),
            (r'\blike,?\s+', ''),
            (r'\bso,?\s+anyway,?\s+', ''),
            
            # Enhanced formal phrase simplifications
            (r'\bin order to\b', 'to'),
            (r'\bdue to the fact that\b', 'because'),
            (r'\bfor the reason that\b', 'because'),
            (r'\bby means of\b', 'using'),
            (r'\bwith regard to\b', 'about'),
            (r'\bin the event that\b', 'if'),
            (r'\bfor the purpose of\b', 'to'),
            (r'\bin connection with\b', 'about'),
            (r'\bwith respect to\b', 'about'),
            (r'\bconcerning the matter of\b', 'about'),
            
            # Enhanced alternatives for common phrases
            (r'\ba large number of\b', 'many'),
            (r'\ba great deal of\b', 'lots of'),
            (r'\bat this point in time\b', 'now'),
            (r'\bin the near future\b', 'soon'),
            (r'\bmake an attempt to\b', 'try to'),
            (r'\bgive consideration to\b', 'consider'),
            (r'\btake into account\b', 'consider'),
            (r'\bcome to the conclusion\b', 'conclude'),
            (r'\bmake a decision\b', 'decide'),
            (r'\bgive assistance to\b', 'help'),
            (r'\bprovide assistance to\b', 'help'),
            
            # Time expression improvements
            (r'\bin the past\b', 'before'),
            (r'\bin the future\b', 'later'),
            (r'\bat the present time\b', 'now'),
            (r'\bcurrently\b', 'now'),
            (r'\bpresently\b', 'now'),
            (r'\bat this moment\b', 'now'),
            
            # Passive voice to active simplifications
            (r'\bwill be completed by\b', 'will finish'),
            (r'\bis being done by\b', 'is doing'),
            (r'\bwas performed by\b', 'did'),
            (r'\bwill be handled by\b', 'will handle'),
            (r'\bis being managed by\b', 'is managing'),
        ]
    
    adjusted = text
    for pattern, replacement in adjustments:
        adjusted = re.sub(pattern, replacement, adjusted, flags=re.IGNORECASE)
    
    # General subtitle optimizations
    adjusted = _optimize_for_subtitles(adjusted)
    
    return adjusted.strip()

def _optimize_for_subtitles(text: str) -> str:
    """
    Apply general subtitle optimizations.
    """
    # Remove redundant punctuation
    text = re.sub(r'[.]{2,}', '...', text)  # Normalize ellipsis
    text = re.sub(r'[!]{2,}', '!', text)    # Single exclamation
    text = re.sub(r'[?]{2,}', '?', text)    # Single question mark
    
    # Fix spacing issues
    text = re.sub(r'\s+', ' ', text)        # Multiple spaces to single
    text = re.sub(r'\s+([.!?,:;])', r'\1', text)  # Remove space before punctuation
    text = re.sub(r'([.!?])\s*([.!?])', r'\1', text)  # Remove duplicate punctuation
    
    # Handle common formatting issues
    text = re.sub(r'\s*-\s*', ' - ', text)  # Normalize dashes
    text = re.sub(r'"\s*([^"]*)\s*"', r'"\1"', text)  # Fix quote spacing
    text = re.sub(r"'\s*([^']*)\s*'", r"'\1'", text)  # Fix single quote spacing
    
    # Ensure proper capitalization after sentence breaks
    def capitalize_after_sentence(match):
        return match.group(1) + match.group(2).upper()
    
    text = re.sub(r'([.!?]\s+)([a-z])', capitalize_after_sentence, text)
    
    # Fix capitalization at the beginning
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    return text.strip()

def apply_style_tone_batch(texts: List[str], target_lang: str = "pl") -> List[str]:
    """
    Apply style and tone adjustments to a batch of texts with enhanced conversational patterns.
    """
    return [adjust_subtitle_style_tone(text, target_lang) for text in texts]

def detect_and_improve_formality(text: str, target_lang: str = "pl") -> str:
    """
    Conservative formality detection with Polish character protection.
    Reduced pattern matching to prevent over-correction.
    """
    if not text.strip():
        return text
    
    # Safety check for Polish characters
    polish_chars = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż', 'Ą', 'Ć', 'Ę', 'Ł', 'Ń', 'Ó', 'Ś', 'Ź', 'Ż']
    original_polish_chars = [char for char in text if char in polish_chars]
    
    # Apply standard style adjustments first
    improved = adjust_subtitle_style_tone(text, target_lang)
    
    # Conservative formality detection - only essential patterns
    if target_lang.lower() == "pl":
        # Only most essential Polish formality patterns to prevent over-correction
        formal_patterns = [
            # Only the most basic and safe formality fixes
            (r'\bproszę\s+o\s+wybaczenie\b', 'przepraszam'),
            (r'\bw\s+chwili\s+obecnej\b', 'teraz'),
            (r'\bobecnie\b', 'teraz'),
        ]
    else:
        # Only most essential English formality patterns
        formal_patterns = [
            # Only the most basic and safe formality fixes
            (r'\bI would like to\b', "I'd like to"),
            (r'\bCould you please\b', 'Can you'),
            (r'\bI beg your pardon\b', 'Sorry'),
            (r'\bAt this point in time\b', 'Now'),
            (r'\bIn the near future\b', 'Soon'),
        ]
    
    # Apply patterns conservatively
    for pattern, replacement in formal_patterns:
        # Check that replacement won't remove Polish characters
        if target_lang.lower() == "pl":
            test_result = re.sub(pattern, replacement, improved, flags=re.IGNORECASE)
            result_polish_chars = [char for char in test_result if char in polish_chars]
            if len(result_polish_chars) >= len(original_polish_chars):
                improved = test_result
        else:
            improved = re.sub(pattern, replacement, improved, flags=re.IGNORECASE)
    
    # Final safety check - if too many Polish characters were lost, return original
    if target_lang.lower() == "pl":
        final_polish_chars = [char for char in improved if char in polish_chars]
        if len(final_polish_chars) < len(original_polish_chars) * 0.8:  # Lost more than 20% of Polish chars
            return text
    
    return improved.strip()

def fix_common_translation_issues(text: str, target_lang: str = "pl") -> str:
    """
    Conservative fix for common translation quality issues with Polish character protection.
    Reduced pattern matching to prevent over-correction and character loss.
    """
    if not text.strip():
        return text
    
    # Safety check for Polish characters
    polish_chars = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż', 'Ą', 'Ć', 'Ę', 'Ł', 'Ń', 'Ó', 'Ś', 'Ź', 'Ż']
    original_polish_chars = [char for char in text if char in polish_chars]
    
    fixed = text
    
    if target_lang.lower() == "pl":
        # Conservative Polish translation fixes - only essential patterns
        translation_fixes = [
            # Only the safest and most essential fixes
            (r'\bja\s+jestem\s+([a-ząćęłńóśźż]+)\b', r'jestem \1'),
            (r'\bja\s+myślę,\s*że\b', 'myślę, że'),
            (r'\bja\s+wiem,\s*że\b', 'wiem, że'),
            (r'\bmam\s+nadzieję\s+na\s+to\b', 'mam nadzieję'),
            (r'\bjest\s+to\s+([a-ząćęłńóśźż]+)\b', r'to \1'),
            (r'\bteraz\s+w\s+tym\s+momencie\b', 'teraz'),
        ]
    else:
        # Conservative English translation fixes - only essential patterns
        translation_fixes = [
            # Only the safest and most essential fixes
            (r'\bI\s+myself\s+personally\b', 'I'),
            (r'\bthat\s+which\s+is\b', 'that is'),
            (r'\bI\s+have\s+the\s+feeling\s+that\b', 'I feel'),
            (r'\bin\s+the\s+case\s+that\b', 'if'),
            (r'\bnow\s+at\s+this\s+moment\b', 'now'),
        ]
    
    # Apply translation fixes conservatively
    for pattern, replacement in translation_fixes:
        # Test the replacement first for Polish text
        if target_lang.lower() == "pl":
            test_result = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
            result_polish_chars = [char for char in test_result if char in polish_chars]
            if len(result_polish_chars) >= len(original_polish_chars):
                fixed = test_result
        else:
            fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
    
    # Apply only essential clarity improvements
    fixed = _improve_sentence_clarity_conservative(fixed, target_lang)
    
    # Final safety check for Polish characters
    if target_lang.lower() == "pl":
        final_polish_chars = [char for char in fixed if char in polish_chars]
        if len(final_polish_chars) < len(original_polish_chars) * 0.8:  # Lost more than 20% of Polish chars
            return text
    
    return fixed.strip()

def _improve_sentence_clarity_conservative(text: str, target_lang: str) -> str:
    """
    Conservative sentence clarity improvement to prevent over-correction.
    """
    if not text.strip():
        return text
    
    improved = text
    
    # Only essential clarity improvements
    clarity_fixes = [
        # Only the safest fixes
        (r'\s+([.!?])', r'\1'),  # space before punctuation
        (r'\s{2,}', ' '),  # multiple spaces
    ]
    
    for pattern, replacement in clarity_fixes:
        improved = re.sub(pattern, replacement, improved, flags=re.IGNORECASE)
    
    return improved.strip()
    

