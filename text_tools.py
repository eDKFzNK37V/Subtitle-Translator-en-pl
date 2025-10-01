from typing import List, Tuple
import re
import torch
from config import DEVICE
from models import GRAMMAR_MODEL, GRAMMAR_TOKENIZER


def clean_translation(text):
    """Remove extra spaces and clean up translation output."""
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def correct_grammar_with_fallback(text: str, confidence_threshold: float = 0.9) -> str:
    """
    Simplified grammar correction with fallback to original text.
    Returns original text if correction fails or produces poor results.
    """
    if not text.strip() or len(text.strip()) < 8:
        return text
    
    try:
        # Try grammar correction
        inputs = GRAMMAR_TOKENIZER.encode("gec: " + text, return_tensors="pt", max_length=200, truncation=True).to(DEVICE)
        with torch.no_grad():
            outputs = GRAMMAR_MODEL.generate(
                inputs,
                max_length=200,
                num_beams=3,
                early_stopping=True
            )
        
        corrected = GRAMMAR_TOKENIZER.decode(outputs[0], skip_special_tokens=True)
        
        # Simple validation: don't change too much
        length_change = abs(len(text) - len(corrected)) / max(len(text), 1)
        if length_change > 0.15:  # More than 15% change is suspicious
            return text
            
        return corrected
    except Exception:
        return text  # Return original on any error


def extract_tags(text):
    """Extract tags from subtitle text."""
    if re.search(r"\$\w+\$", text):
        return text, []
    tags = re.findall(r"{\\.*?}", text)
    clean_text = re.sub(r"{\\.*?}", "", text)
    return clean_text.strip(), tags


def restore_tags(translated, tags):
    """Restore tags to translated text."""
    return "".join(tags) + translated


def group_dialogue_lines(lines: List[str]) -> Tuple[List[str], List[List[int]]]:
    """
    Group dialogue lines for better context during translation.
    Returns grouped text and mapping of original indices.
    """
    if not lines:
        return [], []
    
    grouped = []
    mapping = []
    current_group = []
    current_indices = []
    
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
            
        current_group.append(stripped)
        current_indices.append(idx)
        
        # End group on punctuation or after 3 lines
        if (stripped and stripped[-1] in '.!?' or len(current_group) >= 3):
            grouped.append(' '.join(current_group))
            mapping.append(current_indices[:])
            current_group = []
            current_indices = []
    
    # Don't forget remaining group
    if current_group:
        grouped.append(' '.join(current_group))
        mapping.append(current_indices[:])
    
    return grouped, mapping


def split_grouped_translations(translated_groups: List[str], mapping: List[List[int]]) -> List[str]:
    """
    Split grouped translations back to individual lines.
    """
    if not translated_groups or not mapping:
        return []
    
    # Count total original lines
    max_idx = max(max(group) for group in mapping if group)
    result = [''] * (max_idx + 1)
    
    for group_text, indices in zip(translated_groups, mapping):
        if not indices:
            continue
        
        # Simple split: divide equally among lines
        words = group_text.split()
        words_per_line = max(1, len(words) // len(indices))
        
        for i, idx in enumerate(indices):
            start = i * words_per_line
            end = start + words_per_line if i < len(indices) - 1 else len(words)
            result[idx] = ' '.join(words[start:end])
    
    return result


def extract_newline_tags(text: str) -> Tuple[str, int]:
    """Extract \\N tags from text and count them."""
    n_tags = len(re.findall(r'\\N', text, re.IGNORECASE))
    clean = re.sub(r'\\N', ' ', text, flags=re.IGNORECASE)
    return clean.strip(), n_tags


def insert_newline_tags_at_wordidx(text: str, n_tags: int, word_idx: int) -> str:
    """Insert \\N tags at specified word index."""
    if n_tags <= 0 or not text.strip():
        return text
    
    words = text.split()
    if word_idx <= 0 or word_idx >= len(words):
        # Default: insert in middle
        word_idx = len(words) // 2
    
    # Insert tags
    for _ in range(n_tags):
        if word_idx < len(words):
            words.insert(word_idx, '\\N')
            word_idx += 1
    
    return ' '.join(words)


def clean_duplicate_newline_tags(text: str) -> str:
    """Remove duplicate consecutive \\N tags."""
    return re.sub(r'(\\N\s*)+', r'\\N ', text, flags=re.IGNORECASE).strip()


def insert_newline_tags_contextaware(text: str, n_tags: int, prefer_punctuation: bool = True) -> str:
    """
    Insert \\N tags at natural break points (punctuation or middle).
    """
    if n_tags <= 0 or not text.strip():
        return text
    
    words = text.split()
    if len(words) < 2:
        return text
    
    # Find best insertion point
    if prefer_punctuation:
        # Try to insert after punctuation
        for i, word in enumerate(words[:-1]):
            if word and word[-1] in '.,!?;:':
                for _ in range(n_tags):
                    words.insert(i + 1, '\\N')
                return ' '.join(words)
    
    # Fallback: insert in middle
    mid = len(words) // 2
    for _ in range(n_tags):
        words.insert(mid, '\\N')
    
    return ' '.join(words)


def extract_tags_with_placeholders(text: str) -> Tuple[str, List[Tuple[str, str, int]]]:
    """
    Extract tags and replace with unique placeholders.
    Returns clean text and mapping of (placeholder, original_tag, position).
    """
    if not text:
        return text, []
    
    # Pattern for ASS subtitle tags
    tag_pattern = re.compile(r'(\{\\[^}]+\}|\\[NnHh])')
    
    tags_map = []
    placeholder_text = text
    offset = 0
    
    for match in tag_pattern.finditer(text):
        tag = match.group(0)
        pos = match.start()
        placeholder = f"<TAG{len(tags_map)}>"
        
        tags_map.append((placeholder, tag, pos))
        
        # Replace in text
        start = pos + offset
        end = start + len(tag)
        placeholder_text = placeholder_text[:start] + placeholder + placeholder_text[end:]
        offset += len(placeholder) - len(tag)
    
    return placeholder_text, tags_map


def restore_tags_from_placeholders(translated: str, ph_map: List[Tuple[str, str, int]]) -> str:
    """
    Restore original tags from placeholders in translated text.
    """
    if not ph_map:
        return translated
    
    result = translated
    
    # Replace placeholders with original tags
    for placeholder, original_tag, _ in ph_map:
        result = result.replace(placeholder, original_tag)
    
    # Clean up any remaining placeholders
    result = re.sub(r'<TAG\d+>', '', result)
    
    return result.strip()


def adjust_subtitle_style_tone(text: str, target_lang: str = "pl") -> str:
    """
    Adjust subtitle style for natural tone (simplified version).
    """
    if target_lang.lower() != "pl":
        return text
    
    # Basic Polish style adjustments
    text = re.sub(r'\bja jestem\b', 'jestem', text, flags=re.IGNORECASE)
    text = re.sub(r'"([^"]*)"', r'„\1"', text)  # Polish quotes
    
    return text.strip()


def fix_common_translation_issues(text: str, target_lang: str = "pl") -> str:
    """
    Fix common translation issues (simplified version).
    """
    if not text:
        return text
    
    # Remove extra spaces
    text = clean_translation(text)
    
    # Fix Polish-specific issues if target is Polish
    if target_lang.lower() == "pl":
        text = adjust_subtitle_style_tone(text, target_lang)
    
    return text
