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

def correct_grammar_with_fallback(text: str, confidence_threshold: float = 0.75) -> str:
    """
    Ultra-conservative grammar correction with comprehensive Polish character and name protection.
    Enhanced validation to prevent any character loss or corruption.
    """
    if not text.strip():
        return text
        
    # Pre-correction analysis
    original_char_count = count_polish_characters(text)
    original_names = detect_proper_names(text)
    has_polish_chars = sum(original_char_count.values()) > 0
    
    # Use very high confidence threshold for Polish text
    effective_threshold = confidence_threshold + 0.15 if has_polish_chars else confidence_threshold
    
    # Skip correction for very short text to avoid corruption
    if len(text.strip()) < 5:
        return text
    
    try:
        corrected, confidence = correct_grammar(text)
    except Exception:
        return text  # Return original on any error
    
    # Comprehensive validation checks
    validation_passed = True
    
    # 1. Character preservation check (95% minimum)
    if not validate_character_preservation(text, corrected, 0.95):
        validation_passed = False
    
    # 2. Name preservation check
    if not validate_name_preservation(text, corrected):
        validation_passed = False
    
    # 3. Length change check (reject excessive changes)
    length_change_ratio = abs(len(text) - len(corrected)) / max(len(text), 1)
    if length_change_ratio > 0.25:  # More than 25% length change
        validation_passed = False
    
    # 4. Confidence check
    if confidence < effective_threshold:
        validation_passed = False
    
    # 5. Additional safety: check for corrupted output
    if len(corrected.strip()) < len(text.strip()) * 0.7:  # Lost more than 30% of content
        validation_passed = False
    
    # Return original if any validation fails
    if not validation_passed:
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


def log_names_and_unknown_words(original_lines: list, corrected_lines: list, log_file: str = "correction_log.txt") -> None:
    """
    Log detected names and potentially problematic words for human review.
    Helps identify words that may need special handling during correction.
    """
    import os
    from datetime import datetime
    
    detected_names = set()
    problematic_changes = []
    
    for i, (original, corrected) in enumerate(zip(original_lines, corrected_lines)):
        # Detect names in original text
        names = detect_proper_names(original)
        detected_names.update(names)
        
        # Check for problematic changes
        if original != corrected:
            # Check for significant word changes
            original_words = set(original.split())
            corrected_words = set(corrected.split())
            lost_words = original_words - corrected_words
            added_words = corrected_words - original_words
            
            if lost_words or added_words:
                problematic_changes.append({
                    'line': i + 1,
                    'original': original,
                    'corrected': corrected,
                    'lost_words': list(lost_words),
                    'added_words': list(added_words)
                })
    
    # Write log if there's anything to report
    if detected_names or problematic_changes:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"correction_log_{timestamp}.txt"
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"Correction Analysis Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                if detected_names:
                    f.write("DETECTED NAMES (review for protection):\n")
                    f.write("-" * 40 + "\n")
                    for name in sorted(detected_names):
                        f.write(f"  • {name}\n")
                    f.write("\n")
                
                if problematic_changes:
                    f.write("PROBLEMATIC CORRECTIONS (review for accuracy):\n")
                    f.write("-" * 50 + "\n")
                    for change in problematic_changes:
                        f.write(f"Line {change['line']}:\n")
                        f.write(f"  Original:  {change['original']}\n")
                        f.write(f"  Corrected: {change['corrected']}\n")
                        if change['lost_words']:
                            f.write(f"  Lost words: {', '.join(change['lost_words'])}\n")
                        if change['added_words']:
                            f.write(f"  Added words: {', '.join(change['added_words'])}\n")
                        f.write("\n")
                
                f.write("\nRecommendations:\n")
                f.write("- Review detected names and add to protection list if needed\n")
                f.write("- Check problematic corrections for accuracy\n")
                f.write("- Consider adjusting confidence thresholds if too many changes\n")
                
            print(f"Correction analysis logged to: {log_path}")
        except Exception as e:
            print(f"Warning: Could not write correction log: {e}")

def correct_grammar_batch(texts, confidence_threshold: float = 0.75, enable_logging: bool = True):
    """
    Ultra-conservative batched grammar correction with comprehensive character protection.
    Enhanced protection against Polish character loss and name corruption.
    """
    # Pre-filter very short texts to avoid corruption
    filtered_inputs = []
    filtered_indices = []
    results = []
    
    for i, text in enumerate(texts):
        if len(text.strip()) < 5:
            results.append(text)  # Keep very short texts unchanged
        else:
            filtered_inputs.append(text)
            filtered_indices.append(i)
            results.append(None)  # Placeholder
    
    if not filtered_inputs:
        return results
    
    try:
        inputs = GRAMMAR_TOKENIZER(
            ["gec: " + t for t in filtered_inputs],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=200
        ).to(DEVICE)
        
        with torch.no_grad():
            outputs = GRAMMAR_MODEL.generate(
                inputs.input_ids, 
                attention_mask=inputs.attention_mask,
                max_length=200,
                num_beams=3,
                early_stopping=True,
                output_scores=True,
                return_dict_in_generate=True,
                no_repeat_ngram_size=2
            )
        
        corrected_texts = GRAMMAR_TOKENIZER.batch_decode(outputs.sequences, skip_special_tokens=True)
        
        # Apply comprehensive validation for each correction
        for j, (original, corrected) in enumerate(zip(filtered_inputs, corrected_texts)):
            original_index = filtered_indices[j]
            
            # Use the comprehensive validation function
            validation_passed = True
            
            # 1. Character preservation check
            if not validate_character_preservation(original, corrected, 0.95):
                validation_passed = False
            
            # 2. Name preservation check
            if not validate_name_preservation(original, corrected):
                validation_passed = False
            
            # 3. Length and confidence checks
            length_change_ratio = abs(len(original) - len(corrected)) / max(len(original), 1)
            if length_change_ratio > 0.25:
                validation_passed = False
            
            # 4. Content preservation check
            if len(corrected.strip()) < len(original.strip()) * 0.7:
                validation_passed = False
            
            # Use corrected text only if all validations pass
            if validation_passed:
                results[original_index] = corrected
            else:
                results[original_index] = original
        
        # Log names and problematic corrections if enabled
        if enable_logging:
            try:
                log_names_and_unknown_words(texts, results)
            except Exception:
                pass  # Don't fail on logging errors
        
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
    Ultra-conservative formality detection with comprehensive Polish character protection.
    Includes name preservation and strict validation.
    """
    if not text.strip():
        return text
    
    # Pre-analysis
    original_char_count = count_polish_characters(text)
    original_names = detect_proper_names(text)
    
    # Apply standard style adjustments first
    improved = adjust_subtitle_style_tone(text, target_lang)
    
    # Conservative formality detection - only essential patterns
    if target_lang.lower() == "pl":
        # Only the most basic and safe formality fixes
        formal_patterns = [
            # Only the most essential Polish formality patterns
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
    
    # Apply patterns with strict validation
    for pattern, replacement in formal_patterns:
        test_result = re.sub(pattern, replacement, improved, flags=re.IGNORECASE)
        
        # Validate each change comprehensively
        if test_result != improved:
            if not validate_character_preservation(improved, test_result, 0.98):
                continue  # Skip this pattern
            
            if not validate_name_preservation(improved, test_result):
                continue  # Skip this pattern
                
            # Apply the change only if validation passes
            improved = test_result
    
    # Final comprehensive validation
    if not validate_character_preservation(text, improved, 0.95):
        return text
    
    if not validate_name_preservation(text, improved):
        return text
    
    return improved.strip()

def fix_common_translation_issues(text: str, target_lang: str = "pl") -> str:
    """
    Ultra-conservative fix for common translation quality issues with comprehensive protection.
    Includes Polish character preservation and name protection.
    """
    if not text.strip():
        return text
    
    # Pre-analysis
    original_char_count = count_polish_characters(text)
    original_names = detect_proper_names(text)
    
    fixed = text
    
    if target_lang.lower() == "pl":
        # Only the safest and most essential Polish fixes
        translation_fixes = [
            # Ultra-conservative patterns only
            (r'\bja\s+myślę,\s*że\b', 'myślę, że'),
            (r'\bja\s+wiem,\s*że\b', 'wiem, że'),
            (r'\bmam\s+nadzieję\s+na\s+to\b', 'mam nadzieję'),
            (r'\bteraz\s+w\s+tym\s+momencie\b', 'teraz'),
        ]
    else:
        # Only the safest and most essential English fixes
        translation_fixes = [
            (r'\bI\s+myself\s+personally\b', 'I'),
            (r'\bthat\s+which\s+is\b', 'that is'),
            (r'\bin\s+the\s+case\s+that\b', 'if'),
            (r'\bnow\s+at\s+this\s+moment\b', 'now'),
        ]
    
    # Apply translation fixes with comprehensive validation
    for pattern, replacement in translation_fixes:
        test_result = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
        
        # Validate each change
        if test_result != fixed:
            if not validate_character_preservation(fixed, test_result, 0.98):
                continue  # Skip this pattern
            
            if not validate_name_preservation(fixed, test_result):
                continue  # Skip this pattern
                
            # Apply the change only if validation passes
            fixed = test_result
    
    # Apply only essential clarity improvements
    fixed = _improve_sentence_clarity_conservative(fixed, target_lang)
    
    # Final comprehensive validation
    if not validate_character_preservation(text, fixed, 0.95):
        return text
    
    if not validate_name_preservation(text, fixed):
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
    

