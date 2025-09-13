
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
    inputs = GRAMMAR_TOKENIZER.encode("gec: " + text, return_tensors="pt").to(DEVICE)
    outputs = GRAMMAR_MODEL.generate(inputs, max_length=256, num_beams=5, early_stopping=True)
    return GRAMMAR_TOKENIZER.decode(outputs[0], skip_special_tokens=True)

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
    Returns:
        grouped_lines: List of joined lines for translation
        mapping: List of lists, each sublist contains the original line indices for each group
    """
    grouped_lines = []
    mapping = []
    i = 0
    while i < len(lines):
        group = [lines[i]]
        indices = [i]
        while (
            i + 1 < len(lines)
            and lines[i + 1]
            and lines[i + 1][0].islower()
        ):
            group.append(lines[i + 1])
            indices.append(i + 1)
            i += 1
        grouped_lines.append(" ".join(group))
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
    closest possible position based on original_pos.
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

    offset = 0

    def find_nearest_word_boundary(text, pos):
        # Find left and right word boundaries around pos
        left = re.search(r'\b\w+\b', text[:pos][::-1])
        right = re.search(r'\b\w+\b', text[pos:])
        if left:
            left_pos = pos - left.end()
            return left_pos + len(left.group()), 'after'
        elif right:
            right_pos = pos + right.start()
            return right_pos, 'before'
        return pos, 'exact'

    # Helper: split into words (preserve spaces)
    def split_words_with_spans(text):
        import re
        words = []
        for m in re.finditer(r'\S+', text):
            words.append((m.group(), m.start(), m.end()))
        return words

    orig_words = split_words_with_spans(translated)
    for _placeholder, original, pos in missing:
        # Find the word index in the original text for this tag
        # (ph_map contains original_pos, which is char offset in original text)
        # We'll use the same word index in the translated text
        word_idx = None
        for i, (_w, start, end) in enumerate(split_words_with_spans(translated)):
            if start <= pos < end:
                word_idx = i
                break
        if word_idx is None:
            # If not found, place at start
            insert_at = 0
        else:
            # Place after the same word index in translated text
            words = split_words_with_spans(out)
            if word_idx < len(words):
                insert_at = words[word_idx][1]
            else:
                insert_at = len(out)
        # Insert tag with spaces if needed
        before = out[insert_at-1] if (insert_at > 0 and insert_at-1 < len(out)) else ' '
        after = out[insert_at] if (insert_at < len(out)) else ' '
        tag = original
        if before.isalnum():
            tag = ' ' + tag
        if after.isalnum():
            tag = tag + ' '
        out = out[:insert_at] + tag + out[insert_at:]

    return out


def correct_grammar_batch(texts):
    """
    Batched grammar correction. Falls back to input length if anything fails.
    """
    try:
        inputs = GRAMMAR_TOKENIZER(
            ["gec: " + t for t in texts],
            return_tensors="pt",
            padding=True,
            truncation=True
        ).to(DEVICE)
        outputs = GRAMMAR_MODEL.generate(inputs.input_ids, attention_mask=inputs.attention_mask,
                                         max_length=256, num_beams=5, early_stopping=True)
        return GRAMMAR_TOKENIZER.batch_decode(outputs, skip_special_tokens=True)
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
    

