# subtitle_workflow.py
import os
import torch
from utils import load_subtitle_lines, save_subtitle_lines
from models import get_m2m100_model, get_nllb_model # changed here
from config import DEVICE
from text_tools import extract_tags_with_placeholders, restore_tags_from_placeholders

# Load model once
TRANS_MODEL, TRANS_TOKENIZER = get_m2m100_model()  # changed here
TRANS_MODEL.eval()


def translate_lines(lines, src_lang, tgt_lang, translation_callback=None):
    """
    Translate a list of strings, preserving tag positions via placeholders.
    """
    ph_maps = []
    stripped = []
    for line in lines:
        clean, ph_map = extract_tags_with_placeholders(line)
        stripped.append(clean)
        ph_maps.append(ph_map)

    translated = translate_batch(
        stripped,
        src_lang,
        tgt_lang,
        batch_size=8,
        progress_callback=translation_callback
    )

    restored = []
    for i, text in enumerate(translated):
        restored.append(restore_tags_from_placeholders(text, ph_maps[i]))
    return restored

def translate_subtitles(file_path, src_lang, tgt_lang, polish_only=False, translation_callback=None):
    """
    Load (texts, subs, idx_map), extract placeholders, apply glossary in pipeline,
    translate unless polishing, restore placeholders, and save using idx_map.
    """
    texts, subs, idx_map = load_subtitle_lines(file_path)

    if not texts:
        raise ValueError(f"[translate_subtitles] No subtitle lines loaded from {file_path!r}")

    stripped = []
    ph_maps = []
    from pipeline import apply_glossary

    for line in texts:
        clean, ph_map = extract_tags_with_placeholders(line)
        clean = apply_glossary(clean)
        stripped.append(clean)
        ph_maps.append(ph_map)

    # If polishing only and same language, skip model translate
    if polish_only and src_lang.lower() == tgt_lang.lower():
        translated = stripped[:]
        if translation_callback:
            for idx in range(1, len(translated) + 1):
                translation_callback(idx, len(translated))
    else:
        translated = translate_batch(
            stripped,
            src_lang,
            tgt_lang,
            batch_size=8,
            progress_callback=translation_callback
        )

    restored_lines = [
        restore_tags_from_placeholders(translated[i], ph_maps[i]) for i in range(len(translated))
    ]

    ext = file_path.split('.')[-1].lower()
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.{ext}"
    save_subtitle_lines(restored_lines, output_path, subs, idx_map)

    return output_path, texts, restored_lines

def translate_batch(lines, src_lang, tgt_lang, batch_size=8, progress_callback=None):
    translated = []
    total_lines = len(lines)

    TRANS_TOKENIZER.src_lang = src_lang
    bos_token_id = lambda lang: TRANS_TOKENIZER.get_lang_id(lang)

    for i in range(0, total_lines, batch_size):
        batch = lines[i: i + batch_size]
        encoded = TRANS_TOKENIZER(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True
        ).to(DEVICE)

        with torch.no_grad():
            outputs = TRANS_MODEL.generate(
                **encoded,
                forced_bos_token_id=bos_token_id(tgt_lang),
                max_length=256
            )

        decoded = TRANS_TOKENIZER.batch_decode(outputs, skip_special_tokens=True)

        for idx, text in enumerate(decoded):
            translated.append(text)
            if progress_callback:
                current_line = i + idx + 1
                progress_callback(current_line, total_lines)

    return translated