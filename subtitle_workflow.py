# subtitle_workflow.py
import os
import torch
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from utils import load_subtitle_lines, save_subtitle_lines
from models import get_m2m100_model, get_nllb_globals
from config import DEVICE, selected_engine as global_selected_engine
from text_tools import extract_tags_with_placeholders, restore_tags_from_placeholders

def run_gui_entry():
    from gui import run_gui
    run_gui()
## NLLB language code map (extend as needed)
def model_setup():
    global TRANS_MODEL, TRANS_TOKENIZER
    if global_selected_engine == "nllb":
        TRANS_MODEL, TRANS_TOKENIZER, _ = get_nllb_globals()
        TRANS_MODEL.eval()
    else:
        TRANS_MODEL, TRANS_TOKENIZER = get_m2m100_model()
        TRANS_MODEL.eval()

# Language code maps for each model
NLLB_LANG = {
    "en": "eng_Latn",
    "pl": "pol_Latn",
}
M2M100_LANG = {
    "en": "en",
    "pl": "pl",
}

def get_model_lang_code(lang, model_type):
    if model_type == "nllb":
        return NLLB_LANG.get(lang, lang)
    else:
        return M2M100_LANG.get(lang, lang)

def load_nllb_13b():
    model_id = "facebook/nllb-200-1.3B"
    tok = AutoTokenizer.from_pretrained(model_id)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else None
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id, torch_dtype=dtype)
    model.to(device)
    model.eval()
    return model, tok, device

def translate_batch_nllb(model, tok, device, lines, src_code, tgt_code,
                         max_length=256, num_beams=6, no_repeat_ngram_size=3,
                         length_penalty=1.0):
    """
    Assumes:
      - tok is the NLLB tokenizer
      - src_code/tgt_code are already in NLLB form (e.g. "eng_Latn", "pol_Latn")
    """
    # Directly set the NLLB tokenizer’s src and tgt
    tok.src_lang = src_code
    tgt_id = tok.convert_tokens_to_ids(tgt_code)

    enc = tok(
        lines,
        return_tensors="pt",
        padding=True,
        truncation=True
    ).to(device)

    with torch.no_grad():
        gen = model.generate(
            **enc,
            forced_bos_token_id=tgt_id,
            max_length=max_length,
            num_beams=num_beams,
            no_repeat_ngram_size=no_repeat_ngram_size,
            length_penalty=length_penalty
        )
    return tok.batch_decode(gen, skip_special_tokens=True)

def translate_lines_nllb(model, tok, device, lines, src_lang, tgt_lang,
                         batch_size=16, progress_callback=None):
    # Always use the model and tokenizer passed as arguments (do not overwrite with globals)
    # Map GUI codes ("en","pl") → NLLB codes ("eng_Latn","pol_Latn")
    src_code = get_model_lang_code(src_lang, "nllb")
    tgt_code = get_model_lang_code(tgt_lang, "nllb")
    out = []
    i = 0
    bs = batch_size
    while i < len(lines):
        try:
            batch = lines[i:i+bs]
            preds = translate_batch_nllb(model, tok, device, batch, src_code, tgt_code)
            out.extend(preds)
            i += bs
            if progress_callback:
                progress_callback(min(i, len(lines)), len(lines))
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            bs = max(1, bs // 2)  # halve and retry
            if bs == 1:
                # last resort: process one line
                continue
    return out

def translate_with_context_nllb(
    lines,
    src_lang,
    tgt_lang,
    model,
    tokenizer,
    device,
    beams=6,
    batch_size=16,
    polish_only=False,
    glossary=None,
    translation_callback=None
):
    """
    Context-aware translation with dialogue grouping and robust tag handling.
    - Groups consecutive lines for translation if the next starts with a lowercase letter.
    - Translates grouped lines in context, then splits back to original lines.
    - Preserves tag positions and mapping.
    - Applies glossary pre-translation.
    - Respects polish_only flag.
    """
    from pipeline import apply_glossary, GLOSSARY
    from text_tools import group_dialogue_lines, split_grouped_translations
    model_setup()

    total = len(lines)
    if polish_only and src_lang.lower() == tgt_lang.lower():
        out = []
        for line in lines:
            clean, ph_map = extract_tags_with_placeholders(line)
            clean = apply_glossary(clean, glossary)
            out.append(restore_tags_from_placeholders(clean, ph_map))
        if translation_callback:
            for i in range(1, total + 1):
                translation_callback(i, total)
        return out

    # Group dialogue lines for context-aware translation
    grouped_lines, group_map = group_dialogue_lines(lines)

    # Pre-extract tags/placeholders for all grouped lines
    grouped_clean = []
    grouped_ph_maps = []
    for group in grouped_lines:
        clean, ph_map = extract_tags_with_placeholders(group)
        clean = apply_glossary(clean, glossary)
        grouped_clean.append(clean)
        grouped_ph_maps.append(ph_map)

    # Detect model type by tokenizer/model class name
    model_type = "nllb" if hasattr(tokenizer, "lang_code_to_token") and hasattr(tokenizer, "set_src_lang_special_tokens") else "m2m100"
    src_code = get_model_lang_code(src_lang, model_type)
    tgt_code = get_model_lang_code(tgt_lang, model_type)

    # Translate grouped lines in batches
    translated_groups = []
    for i in range(0, len(grouped_clean), batch_size):
        batch = grouped_clean[i:i+batch_size]
        preds = translate_lines_nllb(model, tokenizer, device, batch, src_lang, tgt_lang, batch_size=batch_size, progress_callback=None)
        translated_groups.extend(preds)
        if translation_callback:
            progress = min(i + len(batch), len(grouped_clean))
            translation_callback(progress, len(grouped_clean))

    # Restore tags for each group
    restored_groups = [restore_tags_from_placeholders(trans, ph_map) for trans, ph_map in zip(translated_groups, grouped_ph_maps)]

    # Split grouped translations back to original lines
    split_lines = split_grouped_translations(restored_groups, group_map)

    if translation_callback:
        for i in range(1, total + 1):
            translation_callback(i, total)

    return split_lines

def correct_text_batch_nllb(lines, src_lang, tgt_lang, glossary=None, translation_callback=None):
    model_setup()
    from pipeline import apply_glossary, GLOSSARY
    stripped, ph_maps = [], []
    for line in lines:
        clean, ph_map = extract_tags_with_placeholders(line)
        clean = apply_glossary(clean, glossary)
        stripped.append(clean)
        ph_maps.append(ph_map)

    model, tok, device = load_nllb_13b()
    translated = translate_lines_nllb(model, tok, device, stripped, src_lang, tgt_lang, progress_callback=translation_callback)
    return [restore_tags_from_placeholders(translated[i], ph_maps[i]) for i in range(len(translated))]



def translate_lines(lines, src_lang, tgt_lang, translation_callback=None, glossary=None):
    """
    Context-aware translation with dialogue grouping and robust tag handling.
    Groups consecutive lines for translation if the next starts with a lowercase letter.
    Translates grouped lines, then splits back to original lines.
    """
    model_setup()  # Ensure correct model/tokenizer is set
    from pipeline import apply_glossary, GLOSSARY
    from text_tools import group_dialogue_lines, split_grouped_translations

    # Group dialogue lines for context-aware translation
    grouped_lines, group_map = group_dialogue_lines(lines)

    # Pre-extract tags/placeholders for all grouped lines
    grouped_clean = []
    grouped_ph_maps = []
    for group in grouped_lines:
        clean, ph_map = extract_tags_with_placeholders(group)
        clean = apply_glossary(clean, glossary)
        grouped_clean.append(clean)
        grouped_ph_maps.append(ph_map)

    # Translate grouped lines
    translated_groups = translate_batch(
        grouped_clean,
        src_lang,
        tgt_lang,
        batch_size=8,
        progress_callback=translation_callback
    )

    # Restore tags for each group
    restored_groups = [restore_tags_from_placeholders(trans, ph_map) for trans, ph_map in zip(translated_groups, grouped_ph_maps)]

    # Split grouped translations back to original lines
    split_lines = split_grouped_translations(restored_groups, group_map)
    return split_lines

def translate_subtitles(file_path, src_lang, tgt_lang, polish_only=False, translation_callback=None, glossary=None):
    """
    Load (texts, subs, idx_map), apply dialogue grouping, tag handling, and context-aware translation.
    """
    model_setup()  # Ensure correct model/tokenizer is set
    from pipeline import apply_glossary, GLOSSARY
    from text_tools import extract_newline_tags, insert_newline_tags_at_wordidx, group_dialogue_lines, split_grouped_translations

    texts, subs, idx_map = load_subtitle_lines(file_path)
    if not texts:
        raise ValueError(f"[translate_subtitles] No subtitle lines loaded from {file_path!r}")

    # --- Remove \N tags and count them ---
    cleaned_lines = []
    n_tag_counts = []
    for line in texts:
        cleaned, n_count = extract_newline_tags(line)
        cleaned_lines.append(cleaned)
        n_tag_counts.append(n_count)

    # Dialogue grouping for context-aware translation
    grouped_lines, group_map = group_dialogue_lines(cleaned_lines)

    # Pre-extract tags/placeholders for all grouped lines
    grouped_clean = []
    grouped_ph_maps = []
    for group in grouped_lines:
        clean, ph_map = extract_tags_with_placeholders(group)
        clean = apply_glossary(clean, glossary)
        grouped_clean.append(clean)
        grouped_ph_maps.append(ph_map)

    # If polishing only and same language, skip model translate
    if polish_only and src_lang.lower() == tgt_lang.lower():
        translated_groups = grouped_clean[:]
        if translation_callback:
            for idx in range(1, len(translated_groups) + 1):
                translation_callback(idx, len(translated_groups))
    else:
        translated_groups = translate_batch(
            grouped_clean,
            src_lang,
            tgt_lang,
            batch_size=8,
            progress_callback=translation_callback
        )

    # Restore tags for each group
    restored_groups = [restore_tags_from_placeholders(trans, ph_map) for trans, ph_map in zip(translated_groups, grouped_ph_maps)]

    # Split grouped translations back to original lines
    restored_lines = split_grouped_translations(restored_groups, group_map)

    # --- Insert \N tags at a fixed word index (e.g. 0 for CLI) ---
    n_wordidx = 0
    final_lines = [
        insert_newline_tags_at_wordidx(line, n_count, n_wordidx)
        for line, n_count in zip(restored_lines, n_tag_counts)
    ]

    ext = file_path.split('.')[-1].lower()
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.{ext}"
    save_subtitle_lines(final_lines, output_path, subs, idx_map)

    return output_path, texts, final_lines

def translate_batch(lines, src_lang, tgt_lang, batch_size=16, progress_callback=None):
    model_setup()  # Ensure correct model/tokenizer is set
    translated = []
    total_lines = len(lines)


    # Detect model type by tokenizer/model class name
    model_type = "nllb" if hasattr(TRANS_TOKENIZER, "lang_code_to_token") and hasattr(TRANS_TOKENIZER, "set_src_lang_special_tokens") else "m2m100"
    src_code = get_model_lang_code(src_lang, model_type)
    tgt_code = get_model_lang_code(tgt_lang, model_type)
    TRANS_TOKENIZER.src_lang = src_code
    bos_token_id = lambda lang: TRANS_TOKENIZER.get_lang_id(get_model_lang_code(lang, model_type))

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

