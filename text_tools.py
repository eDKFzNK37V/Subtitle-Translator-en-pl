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
    tags = re.findall(r"{\\.*?}", text)
    clean_text = re.sub(r"{\\.*?}", "", text)
    return clean_text, tags

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

TAG_OR_ESCAPE = re.compile(r"({\\.*?})|(\\[NnHhRr])")

def extract_tags_with_placeholders(text: str):
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

    clean_text = TAG_OR_ESCAPE.sub(repl, text)
    return clean_text, ph_map

def restore_tags_from_placeholders(translated: str, ph_map):
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
    import re

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

    for _placeholder, original, pos in missing:
        insert_at, direction = find_nearest_word_boundary(out, pos + offset)
        if direction == 'before':
            out = out[:insert_at] + original + out[insert_at:]
        else:
            out = out[:insert_at + len(original)] + original + out[insert_at + len(original):]
        offset += len(original)

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
    

