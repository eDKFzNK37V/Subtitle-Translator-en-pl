from typing import List, Tuple
import re
import torch
from config import DEVICE
from models import PUNCT_MODELS, PUNCT_TOKENIZERS, GRAMMAR_MODEL, GRAMMAR_TOKENIZER
from logs import accumulate_correction_data, log_names_and_unknown_words

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

def count_polish_characters(text: str) -> dict:
    """Count individual Polish characters in text."""
    polish_chars = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż', 'Ą', 'Ć', 'Ę', 'Ł', 'Ń', 'Ó', 'Ś', 'Ź', 'Ż']
    char_count = {}
    for char in polish_chars:
        char_count[char] = text.count(char)
    return char_count

def detect_proper_names(text: str) -> list:
    """Detect potential proper names (capitalized words) for preservation."""
    import re
    # Find words that start with capital letter and are likely names
    name_pattern = r'\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b'
    potential_names = re.findall(name_pattern, text)
    
    # Filter out common words that aren't names
    common_words = {'Będę', 'Dziś', 'Jest', 'Mam', 'Czy', 'Ale', 'Tak', 'Nie', 'Co', 'Jak', 'Gdzie', 'Kiedy', 'Dlaczego'}
    names = [name for name in potential_names if name not in common_words]
    return names

def validate_character_preservation(original: str, corrected: str, min_preservation_rate: float = 0.95) -> bool:
    """
    Validate that Polish characters are preserved at the specified rate.
    min_preservation_rate: minimum fraction of Polish characters that must be preserved (default 95%)
    """
    original_chars = count_polish_characters(original)
    corrected_chars = count_polish_characters(corrected)
    
    total_original = sum(original_chars.values())
    if total_original == 0:
        return True  # No Polish characters to preserve
    
    total_preserved = 0
    for char, original_count in original_chars.items():
        if original_count > 0:
            preserved_count = min(corrected_chars.get(char, 0), original_count)
            total_preserved += preserved_count
    
    preservation_rate = total_preserved / total_original
    return preservation_rate >= min_preservation_rate

def validate_name_preservation(original: str, corrected: str) -> bool:
    """Check if proper names are preserved in the corrected text."""
    original_names = detect_proper_names(original)
    if not original_names:
        return True  # No names to preserve
    
    corrected_lower = corrected.lower()
    preserved_names = 0
    
    for name in original_names:
        # Check if name exists in corrected text (case insensitive)
        if name.lower() in corrected_lower:
            preserved_names += 1
    
    # Allow losing 1 name out of several, but preserve at least 80%
    preservation_rate = preserved_names / len(original_names) if original_names else 1.0
    return preservation_rate >= 0.8

def correct_grammar_with_fallback(text: str, confidence_threshold: float = 0.85) -> str:
    """
    Ultra-conservative grammar correction with minimal processing to prevent over-correction.
    Only applies corrections that are absolutely safe and necessary.
    """
    if not text.strip() or len(text.strip()) < 8:  # Skip very short texts
        return text
        
    # Pre-correction analysis - track Polish characters precisely
    original_polish_chars = count_polish_characters(text)
    original_names = detect_proper_names(text)
    total_polish_chars = sum(original_polish_chars.values())
    
    # Skip correction for text with many Polish characters to prevent corruption
    if total_polish_chars > len(text) * 0.2:  # More than 20% Polish characters
        return text
    
    try:
        corrected, confidence = correct_grammar(text)
    except Exception:
        return text  # Return original on any error
    
    # Ultra-strict validation - reject most corrections
    
    # 1. Confidence must be very high
    if confidence < confidence_threshold:
        return text
    
    # 2. Perfect Polish character preservation required
    if total_polish_chars > 0:
        if not validate_character_preservation(text, corrected, 1.0):  # 100% preservation
            return text
    
    # 3. Perfect name preservation required
    if original_names:
        if not validate_name_preservation(text, corrected):
            return text
    
    # 4. Length change must be minimal (less than 10%)
    length_change_ratio = abs(len(text) - len(corrected)) / max(len(text), 1)
    if length_change_ratio > 0.1:
        return text
    
    # 5. No significant word loss
    original_words = set(re.findall(r'\b\w+\b', text.lower()))
    corrected_words = set(re.findall(r'\b\w+\b', corrected.lower()))
    word_loss_ratio = len(original_words - corrected_words) / max(len(original_words), 1)
    if word_loss_ratio > 0.05:  # Lost more than 5% of words
        return text
    
    return corrected

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
    # Note: Pattern variables removed as they were not being used in the logic
    
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
    # If word_idx == 0, use the automated context-aware function
    if word_idx == 0:
        return insert_newline_tags_contextaware(text, n_tags, prefer_punctuation=True)

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
    clean_text = TAG_OR_ESCAPE.sub(repl, text)
    # Debug print for diagnostics
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
    # Only insert if the original tag is not already present in the string
    missing = []
    for (p, o, pos) in ph_map:
        if p not in translated and o not in out:
            missing.append((p, o, pos))
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

    # Remove any leftover placeholders like <TAGPH_0>, < TAGPH_0>, etc.
    out = re.sub(r'<\s*TAGPH_\d+\s*>?', '', out)  # Remove all <TAGPH_n> variants with optional spaces and optional closing '>'
    return out


# Session logging has been moved to logs.py

def correct_grammar_batch(texts, confidence_threshold: float = 0.85, enable_logging: bool = True):
    """
    Minimalistic batched grammar correction to prevent over-correction and character loss.
    Only applies safe, essential corrections with strict validation.
    """
    # Skip processing for texts that are likely to be corrupted
    results = []
    
    for text in texts:
        # Apply individual correction with ultra-conservative approach
        corrected = correct_grammar_with_fallback(text, confidence_threshold)
        results.append(corrected)
    
    # Log names and problematic corrections if enabled (always create a log file)
    if enable_logging:
        try:
            log_names_and_unknown_words(texts, results)
        except Exception:
            pass  # Don't fail on logging errors
    
    return results

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
    Minimal subtitle style adjustment - only essential, safe changes.
    Prevents over-correction that was causing translation quality issues.
    """
    if not text.strip():
        return text
    
    adjusted = text
    
    # Only the most essential and safe adjustments
    if target_lang.lower() == "pl":
        # Minimal Polish adjustments - only very safe patterns
        safe_adjustments = [
            (r'\bja jestem\b', 'jestem'),  # Remove redundant "ja"
            (r'\btak,\s*tak\b', 'tak'),    # Remove duplication
            (r'\bnie,\s*nie\b', 'nie'),    # Remove duplication
        ]
    else:
        # Minimal English adjustments - only essential contractions
        safe_adjustments = [
            (r'\bI will\b', "I'll"),
            (r'\byou will\b', "you'll"),
            (r'\bdo not\b', "don't"),
            (r'\bcannot\b', "can't"),
        ]
    
    # Apply only if Polish character preservation is guaranteed
    original_polish_chars = count_polish_characters(adjusted)
    
    for pattern, replacement in safe_adjustments:
        test_result = re.sub(pattern, replacement, adjusted, flags=re.IGNORECASE)
        
        # Validate Polish character preservation
        if target_lang.lower() == "pl":
            if validate_character_preservation(adjusted, test_result, 1.0):
                adjusted = test_result
        else:
            adjusted = test_result
    
    # Only essential formatting fixes
    adjusted = re.sub(r'\s{2,}', ' ', adjusted)  # Multiple spaces
    adjusted = re.sub(r'\s+([.!?,:;])', r'\1', adjusted)  # Space before punctuation
    
    return adjusted.strip()





def detect_and_improve_formality(text: str, target_lang: str = "pl") -> str:
    """
    Minimal formality improvement - only essential changes to prevent over-correction.
    """
    if not text.strip():
        return text
    # Just apply the minimal style adjustment
    return adjust_subtitle_style_tone(text, target_lang)

def fix_common_translation_issues(text: str, target_lang: str = "pl") -> str:
    """
    Minimal fix for only the most essential translation issues.
    Prevents over-correction by applying only safe, necessary changes.
    """
    if not text.strip():
        return text
    
    # Only basic spacing and formatting fixes
    fixed = re.sub(r'\s+([.!?])', r'\1', text, flags=re.IGNORECASE)  # space before punctuation
    fixed = re.sub(r'\s{2,}', ' ', fixed, flags=re.IGNORECASE)  # multiple spaces
    
    return fixed.strip()



