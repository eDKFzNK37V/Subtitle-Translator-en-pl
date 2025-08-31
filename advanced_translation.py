# advanced.translation.py
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

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
