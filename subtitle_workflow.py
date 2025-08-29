# subtitle_workflow.py
import os
import torch
from text_tools   import extract_tags, restore_tags
from pipeline     import correct_text_batch
from utils        import load_subtitle_lines, save_subtitle_lines
from models       import get_translation_model
from config       import DEVICE

# Load model once
TRANS_MODEL, TRANS_TOKENIZER = get_translation_model()

def translate_subtitles(file_path, src_lang, tgt_lang, polish_only=False, translation_callback=None):
    originals, subs = load_subtitle_lines(file_path)
    if subs is None:
        subs = []

    tag_map = []
    if subs:
        stripped = []
        for ev in subs:
            clean, tags = extract_tags(ev.text)
            stripped.append(clean)
            tag_map.append(tags)
    else:
        stripped = originals

    translated = translate_batch(
        stripped,
        src_lang,
        tgt_lang,
        batch_size=8,
        progress_callback=translation_callback
    )

    # Restore tags
    restored_lines = []
    if tag_map:
        for i, line in enumerate(translated):
            restored = restore_tags(line, tag_map[i])
            restored_lines.append(restored)
            subs[i].text = restored
    else:
        restored_lines = translated

    # Save file
    ext = file_path.split('.')[-1].lower()
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.{ext}"
    save_subtitle_lines(restored_lines, output_path, subs)

    return output_path, originals, restored_lines

def translate_batch(lines, src_lang, tgt_lang, batch_size=8, progress_callback=None):
    translated = []
    total_lines = len(lines)

    TRANS_TOKENIZER.src_lang = src_lang
    bos_token_id = lambda lang: TRANS_TOKENIZER.get_lang_id(lang)

    for i in range(0, total_lines, batch_size):
        batch = lines[i : i + batch_size]
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

        # Emit per-line callbacks
        for idx, text in enumerate(decoded):
            translated.append(text)
            if progress_callback:
                current_line = i + idx + 1
                progress_callback(current_line, total_lines)

    return translated