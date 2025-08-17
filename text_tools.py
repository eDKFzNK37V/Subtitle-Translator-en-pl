import re
from functools import lru_cache
import torch
from config import DEVICE
from models import PUNCT_MODELS, PUNCT_TOKENIZERS, GRAMMAR_MODEL, GRAMMAR_TOKENIZER
from resources import DIACRITIC_DICT

@lru_cache(maxsize=4096)
def restore_diacritics(text: str) -> str:
    words = []
    for w in text.split():
        lw = w.lower()
        if lw in DIACRITIC_DICT:
            if w.isupper():
                words.append(DIACRITIC_DICT[lw].upper())
            elif w.istitle():
                words.append(DIACRITIC_DICT[lw].capitalize())
            else:
                words.append(DIACRITIC_DICT[lw])
        else:
            words.append(w)
    return " ".join(words)

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

def extract_tags(text):
    if re.search(r"\$\w+\$", text):
        return text, []
    tags = re.findall(r"{\\.*?}", text)
    clean_text = re.sub(r"{\\.*?}", "", text)
    return clean_text.strip(), tags

def restore_tags(translated, tags):
    return "".join(tags) + translated

# Combined pipeline function
def correct_text_pipeline(text, lang):
    if lang.lower() == "pl":
        text = restore_diacritics(text)
    text = correct_grammar(text)
    text = correct_punctuation(text)
    return clean_translation(text)
