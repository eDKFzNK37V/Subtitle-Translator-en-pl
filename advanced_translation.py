# advanced.translation.py
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from text_tools import extract_tags_with_placeholders, restore_tags_from_placeholders
from pipeline import apply_glossary

# Minimal UI→NLLB language code map (extend as needed)
NLLB_LANG = {
    "en": "eng_Latn",
    "pl": "pol_Latn",
}

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
    enc = tok(
        lines,
        return_tensors="pt",
        padding=True,
        truncation=True,
        src_lang=src_code
    ).to(device)
    tgt_id = tok.convert_tokens_to_ids(tgt_code)
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

def translate_lines_nllb(model, tok, device, lines, src, tgt,
                         batch_size=16, progress_callback=None):
    src_code = NLLB_LANG[src]
    tgt_code = NLLB_LANG[tgt]
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
    translation_callback=None
):
    """
    Translate lines with small context windows using NLLB.
    - Preserves order and length.
    - Applies glossary pre-translation.
    - Respects polish_only flag.
    """

    total = len(lines)
    result = []
    overlap = 2

    # No translation if polishing only and langs match
    if polish_only and src_lang.lower() == tgt_lang.lower():
        out = []
        for line in lines:
            clean, ph_map = extract_tags_with_placeholders(line)
            clean = apply_glossary(clean)
            out.append(restore_tags_from_placeholders(clean, ph_map))
        if translation_callback:
            for i in range(1, total + 1):
                translation_callback(i, total)
        return out

    # Pre-extract tags/placeholders for all lines
    clean_lines = []
    ph_maps = []
    for line in lines:
        clean, ph_map = extract_tags_with_placeholders(line)
        clean_lines.append(apply_glossary(clean))
        ph_maps.append(ph_map)

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        ctx_start = max(0, start - overlap)
        ctx_end = min(total, end + overlap)

        # Context window is clean text
        window = [clean_lines[i] for i in range(ctx_start, ctx_end)]

        # You need to implement translate_lines_nllb to use the passed model/tokenizer
        trans_window = translate_lines_nllb(
            window, src_lang, tgt_lang, model, tokenizer, device, beams, progress_callback=translation_callback
        )
        offset = start - ctx_start
        batch_translated = trans_window[offset:offset + (end - start)]

        # Restore tags for each line in this batch
        for rel_idx, text in enumerate(batch_translated):
            orig_idx = start + rel_idx
            restored = restore_tags_from_placeholders(text, ph_maps[orig_idx])
            result.append(restored)

        if translation_callback:
            for i in range(start + 1, end + 1):
                translation_callback(i, total)

    return result


