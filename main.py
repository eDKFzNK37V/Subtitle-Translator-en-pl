import os
import re
import torch
import pysubs2
from functools import lru_cache
import tkinter as tk
from tkinter import filedialog, messagebox
from tqdm import tqdm
from transformers import (
    M2M100ForConditionalGeneration,
    M2M100Tokenizer,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    pipeline,
    AutoModelForTokenClassification
)

# === DEVICE SETUP ===
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# === MODELS ===
print("Loading translation model...")
TRANS_MODEL = M2M100ForConditionalGeneration.from_pretrained(
    "facebook/m2m100_418M"
).to(DEVICE)
TRANS_TOKENIZER = M2M100Tokenizer.from_pretrained("facebook/m2m100_418M")

print("Loading grammar correction model...")
GRAMMAR_MODEL = AutoModelForSeq2SeqLM.from_pretrained(
    "prithivida/grammar_error_correcter_v1"
).to(DEVICE)
GRAMMAR_TOKENIZER = AutoTokenizer.from_pretrained(
    "prithivida/grammar_error_correcter_v1"
)

print("Loading punctuation models...")
PUNCT_MODELS = {
    "kredor": AutoModelForTokenClassification.from_pretrained(
        "kredor/punctuate-all"
    ).to(DEVICE),
    "oliverguhr": AutoModelForTokenClassification.from_pretrained(
        "oliverguhr/fullstop-punctuation-multilang-large"
    ).to(DEVICE),
}
PUNCT_TOKENIZERS = {
    "kredor": AutoTokenizer.from_pretrained("kredor/punctuate-all"),
    "oliverguhr": AutoTokenizer.from_pretrained(
        "oliverguhr/fullstop-punctuation-multilang-large"
    ),
}

# Load special words into a set for fast lookup
# Load dictionary into a mapping for diacritic restoration
DIACRITIC_DICT = {}
with open(r"F:\Subtitle Translator\components\polish_words_with_specials.txt", encoding="utf-8") as f:
    for line in f:
        word = line.strip()
        if word:
            DIACRITIC_DICT[word.lower()] = word



# === HELPERS ===
@lru_cache(maxsize=4096)
def restore_diacritics(text: str) -> str:
    """Restore Polish diacritics using the local dictionary."""
    restored_words = []
    for w in text.split():
        lw = w.lower()
        if lw in DIACRITIC_DICT:
            # Preserve case style
            if w.isupper():
                restored_words.append(DIACRITIC_DICT[lw].upper())
            elif w.istitle():
                restored_words.append(DIACRITIC_DICT[lw].capitalize())
            else:
                restored_words.append(DIACRITIC_DICT[lw])
        else:
            restored_words.append(w)
    return " ".join(restored_words)


def correct_punctuation(text, model_choice="kredor"):
    model = PUNCT_MODELS[model_choice]
    tokenizer = PUNCT_TOKENIZERS[model_choice]
    tokens = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(
        DEVICE
    )
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
            punct = {
                "LABEL_COMMA": ",",
                "LABEL_PERIOD": ".",
                "LABEL_QUESTION": "?",
            }.get(label, "")
            current_word += punct
    if current_word:
        corrected_words.append(current_word)
    return " ".join(corrected_words)


def correct_grammar(text):
    inputs = GRAMMAR_TOKENIZER.encode(
        "gec: " + text, return_tensors="pt"
    ).to(DEVICE)
    outputs = GRAMMAR_MODEL.generate(
        inputs, max_length=256, num_beams=5, early_stopping=True
    )
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


def correct_text(text, lang):
    if lang.lower() == "pl":
        text = restore_diacritics(text)
    if lang.lower() == "en":
        text = correct_grammar(text)
    text = correct_punctuation(text, "kredor")  # fixed choice
    return clean_translation(text)




def translate_batch(lines, src_lang, tgt_lang, batch_size=8):
    TRANS_TOKENIZER.src_lang = src_lang
    bos_token_id = TRANS_TOKENIZER.get_lang_id(tgt_lang)
    translated = []
    total_batches = (len(lines) + batch_size - 1) // batch_size
    progress = tqdm(
        total=total_batches,
        desc="Translating",
        unit="batch",
        colour="green",
        dynamic_ncols=True,
    )
    for i in range(0, len(lines), batch_size):
        batch = lines[i : i + batch_size]
        encoded = TRANS_TOKENIZER(
            batch, return_tensors="pt", padding=True, truncation=True
        ).to(DEVICE)
        outputs = TRANS_MODEL.generate(
            **encoded, forced_bos_token_id=bos_token_id, max_length=256
        )
        decoded = TRANS_TOKENIZER.batch_decode(outputs, skip_special_tokens=True)
        translated.extend(decoded)
        progress.update(1)
    progress.close()
    return translated


# === MAIN ===
def translate_subtitles(file_path, src_lang, tgt_lang, polish_only=False):
    subs = pysubs2.load(file_path, encoding="utf-8")
    originals = []
    tag_map = []
    for event in subs:
        clean, tags = extract_tags(event.text)
        originals.append(clean)
        tag_map.append(tags)
    if polish_only:
        translated_lines = originals
    else:
        translated_lines = translate_batch(originals, src_lang, tgt_lang)
    log_path = os.path.splitext(file_path)[0] + "_log.txt"
    with open(log_path, "w", encoding="utf-8") as log_file:
        for i, event in enumerate(subs):
            translated = clean_translation(translated_lines[i])
            corrected = correct_text(translated, tgt_lang)
            event.text = restore_tags(corrected, tag_map[i])
            log_file.write(f"Original:   {originals[i]}\n")
            log_file.write(f"Translated: {translated}\n")
            log_file.write(f"Corrected:  {corrected}\n\n")
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.ass"
    subs.save(output_path, encoding="utf-8")
    return output_path


# === GUI ===
def run_gui():
    def browse_file():
        file_path.set(filedialog.askopenfilename(filetypes=[("ASS Subtitle", "*.ass")]))

    def start_translation():
        path = file_path.get()
        src = src_lang.get()
        tgt = tgt_lang.get()
        if not path or not src or not tgt:
            messagebox.showerror("Error", "Please fill all fields.")
            return
        try:
            output = translate_subtitles(path, src, tgt, polish_only.get())
            messagebox.showinfo("Success", f"Translated file saved to:\n{output}")
        except Exception as e:
            messagebox.showerror("Translation Failed", str(e))

    root = tk.Tk()
    root.title("ASS Subtitle Translator")
    file_path = tk.StringVar()
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")
    polish_only = tk.BooleanVar(value=False)

    tk.Label(root, text="Subtitle File (.ass):").grid(row=0, column=0, sticky="w")
    tk.Entry(root, textvariable=file_path, width=40).grid(row=0, column=1)
    tk.Button(root, text="Browse", command=browse_file).grid(row=0, column=2)

    tk.Label(root, text="Source Language Code:").grid(row=1, column=0, sticky="w")
    tk.Entry(root, textvariable=src_lang, width=10).grid(row=1, column=1)

    tk.Label(root, text="Target Language Code:").grid(row=2, column=0, sticky="w")
    tk.Entry(root, textvariable=tgt_lang, width=10).grid(row=2, column=1)

    tk.Label(root, text="Polish Only:").grid(row=3, column=0, sticky="w")
    tk.Checkbutton(root, variable=polish_only).grid(row=3, column=1, sticky="w")

    tk.Button(root, text="Start Translation", command=start_translation).grid(row=5, column=0, columnspan=3)

    root.mainloop()

if __name__ == "__main__":
    run_gui()
