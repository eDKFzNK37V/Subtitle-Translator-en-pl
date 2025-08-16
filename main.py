import os
import re
import torch
import pysubs2
import tkinter as tk
from tkinter import filedialog, messagebox
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import (
    M2M100ForConditionalGeneration,
    M2M100Tokenizer,
    AutoTokenizer,
    AutoModelForSeq2SeqLM
)

# === MODEL SETUP ===
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Translation model
TRANS_MODEL = M2M100ForConditionalGeneration.from_pretrained("facebook/m2m100_418M").to(DEVICE)
TRANS_TOKENIZER = M2M100Tokenizer.from_pretrained("facebook/m2m100_418M")

# Grammar correction model
GRAMMAR_MODEL = AutoModelForSeq2SeqLM.from_pretrained("prithivida/grammar_error_correcter_v1").to(DEVICE)
GRAMMAR_TOKENIZER = AutoTokenizer.from_pretrained("prithivida/grammar_error_correcter_v1")
# === PUNCTUATION MODEL SETUP ===
# === PUNCTUATION MODELS ===
PUNCT_MODELS = {
    "kredor": AutoModelForTokenClassification.from_pretrained("kredor/punctuate-all").to(DEVICE),
    "oliverguhr": AutoModelForTokenClassification.from_pretrained("oliverguhr/fullstop-punctuation-multilang-large").to(DEVICE)
}

PUNCT_TOKENIZERS = {
    "kredor": AutoTokenizer.from_pretrained("kredor/punctuate-all"),
    "oliverguhr": AutoTokenizer.from_pretrained("oliverguhr/fullstop-punctuation-multilang-large")
}


# === PUNCTUATION CORRECTION ===
def correct_punctuation(text, model_choice="kredor"):
    model     = PUNCT_MODELS[model_choice]
    tokenizer = PUNCT_TOKENIZERS[model_choice]

    tokens = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(DEVICE)
    with torch.no_grad():
        logits = model(**tokens).logits

    preds     = torch.argmax(logits, dim=2)[0]
    input_ids = tokens["input_ids"][0]
    labels    = model.config.id2label

    corrected_words = []
    current_word    = ""

    for token_id, pred_id in zip(input_ids, preds):
        token = tokenizer.convert_ids_to_tokens(token_id.item())
        label = labels[pred_id.item()]

        # skip special tokens
        if token in ["<s>", "</s>", "<pad>", "<unk>"]:
            continue

        # SentencePiece: new word if starts with ▁
        if token.startswith("▁"):
            if current_word:
                corrected_words.append(current_word)
            current_word = token[1:]
        else:
            current_word += token

        # append punctuation if any
        if label != "O":
            punct = {
                "LABEL_COMMA":    ",",
                "LABEL_PERIOD":   ".",
                "LABEL_QUESTION": "?"
            }.get(label, "")
            current_word += punct

    if current_word:
        corrected_words.append(current_word)

    return " ".join(corrected_words)


# === DIACRITICS RESTORATION (via back-translation) ===
def restore_diacritics(text):
    # Polish → English
    TRANS_TOKENIZER.src_lang = "pl"
    enc_pl = TRANS_TOKENIZER(text, return_tensors="pt", truncation=True, padding=True).to(DEVICE)
    en_id  = TRANS_TOKENIZER.get_lang_id("en")
    out_en = TRANS_MODEL.generate(**enc_pl, forced_bos_token_id=en_id, max_length=128)
    english = TRANS_TOKENIZER.decode(out_en[0], skip_special_tokens=True)

    # English → Polish
    TRANS_TOKENIZER.src_lang = "en"
    enc_en   = TRANS_TOKENIZER(english, return_tensors="pt", truncation=True, padding=True).to(DEVICE)
    pl_id    = TRANS_TOKENIZER.get_lang_id("pl")
    out_pl   = TRANS_MODEL.generate(**enc_en, forced_bos_token_id=pl_id, max_length=128)
    return TRANS_TOKENIZER.decode(out_pl[0], skip_special_tokens=True)


# === SMART CORRECTION ROUTER ===
def correct_text(text, lang, model_choice="kredor"):
    # 1) If Polish, restore diacritics first
    if lang.lower() == "pl":
        text = restore_diacritics(text)

    # 2) If English, grammar‐correct before punctuation
    if lang.lower() == "en":
        text = correct_grammar(text)

    # 3) Always punctuate
    text = correct_punctuation(text, model_choice)

    # 4) Final cleanup (spacing, etc.)
    return clean_translation(text)


# === MAIN FUNCTION ===
def translate_subtitles(
    file_path,
    src_lang,
    tgt_lang,
    polish_only=False,
    model_choice="kredor"
):
    subs = pysubs2.load(file_path, encoding="utf-8")
    originals = []
    tag_map   = []

    for event in subs:
        clean, tags = extract_tags(event.text)
        originals.append(clean)
        tag_map.append(tags)

    # Either translate or pass through originals
    if polish_only:
        translated_lines = originals
    else:
        translated_lines = translate_batch(originals, src_lang, tgt_lang)

    # Process each line
    log_path = os.path.splitext(file_path)[0] + "_log.txt"
    with open(log_path, "w", encoding="utf-8") as log_file:
        for i, event in enumerate(subs):
            translated = clean_translation(translated_lines[i])
            corrected  = correct_text(translated, tgt_lang, model_choice)

            # restore any ASS tags & write out
            event.text = restore_tags(corrected, tag_map[i])
            log_file.write(f"Original:   {originals[i]}\n")
            log_file.write(f"Translated: {translated}\n")
            log_file.write(f"Corrected:  {corrected}\n\n")

    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.ass"
    subs.save(output_path, encoding="utf-8")
    return output_path



# === TAG PRESERVATION ===
def extract_tags(text):
    if re.search(r"\$\w+\$", text):
        return text, []
    tags = re.findall(r"{\\.*?}", text)
    clean_text = re.sub(r"{\\.*?}", "", text)
    return clean_text.strip(), tags

def restore_tags(translated, tags):
    return "".join(tags) + translated

# === GRAMMAR CORRECTION ===
def correct_grammar(text):
    inputs = GRAMMAR_TOKENIZER.encode("gec: " + text, return_tensors="pt").to(DEVICE)
    outputs = GRAMMAR_MODEL.generate(inputs, max_length=256, num_beams=5, early_stopping=True)
    return GRAMMAR_TOKENIZER.decode(outputs[0], skip_special_tokens=True)

# === TRANSLATION ===
def translate_batch(lines, src_lang, tgt_lang, batch_size=8):
    TRANS_TOKENIZER.src_lang = src_lang
    bos_token_id = TRANS_TOKENIZER.get_lang_id(tgt_lang)
    translated = []

    total_batches = (len(lines) + batch_size - 1) // batch_size
    progress = tqdm(total=total_batches, desc="Translating", unit="batch", colour="green", dynamic_ncols=True)

    for i in range(0, len(lines), batch_size):
        batch = lines[i:i+batch_size]
        encoded = TRANS_TOKENIZER(batch, return_tensors="pt", padding=True, truncation=True).to(DEVICE)
        outputs = TRANS_MODEL.generate(**encoded, forced_bos_token_id=bos_token_id, max_length=256)
        decoded = TRANS_TOKENIZER.batch_decode(outputs, skip_special_tokens=True)
        translated.extend(decoded)
        progress.update(1)

    progress.close()
    return translated




# === CLEANUP ===
def clean_translation(text):
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()






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
            output = translate_subtitles(path, src, tgt, polish_only.get(), model_choice.get())
            messagebox.showinfo("Success", f"Translated file saved to:\n{output}")
        except Exception as e:
            messagebox.showerror("Translation Failed", str(e))

    root = tk.Tk()
    root.title("ASS Subtitle Translator")

    file_path = tk.StringVar()
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")

    tk.Label(root, text="Subtitle File (.ass):").grid(row=0, column=0, sticky="w")
    tk.Entry(root, textvariable=file_path, width=40).grid(row=0, column=1)
    tk.Button(root, text="Browse", command=browse_file).grid(row=0, column=2)

    tk.Label(root, text="Source Language Code:").grid(row=1, column=0, sticky="w")
    tk.Entry(root, textvariable=src_lang).grid(row=1, column=1)

    tk.Label(root, text="Target Language Code:").grid(row=2, column=0, sticky="w")
    tk.Entry(root, textvariable=tgt_lang).grid(row=2, column=1)
    polish_only = tk.BooleanVar(value=False)
    tk.Checkbutton(root, text="Correct Polish file only (no translation)", variable=polish_only).grid(row=3, column=0, sticky="w")
    model_choice = tk.StringVar(value="kredor")
    tk.Label(root, text="Punctuation Model:").grid(row=4, column=0, sticky="w")
    tk.OptionMenu(root, model_choice, "kredor", "oliverguhr").grid(row=4, column=1, sticky="w")

    tk.Button(root, text="Translate", command=start_translation, bg="lightblue").grid(row=3, column=1, pady=10)

    root.mainloop()

# === RUN ===
if __name__ == "__main__":
    run_gui()



sample_lines = [
    "cześć jak się czujesz",
    "dobrze się czuję dziękuję",
    "to jest test z pogrubieniem i kursywą",
    "oto linia dialogu która powinna być poprawiona",
    "czy możemy połączyć język polski i angielski"
]
if __name__ == "__main__":
    print("=== Polish Correction Test ===")
    for line in sample_lines:
        corrected = correct_text(line, "pl")
        print(f"Original:  {line}")
        print(f"Corrected: {corrected}")
        print("-" * 40)
