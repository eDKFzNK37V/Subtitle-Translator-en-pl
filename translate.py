from tqdm import tqdm
from config import DEVICE
from models import get_translation_model

# Load model once
TRANS_MODEL, TRANS_TOKENIZER = get_translation_model()

def translate_batch(lines, src_lang, tgt_lang, batch_size=8):
    TRANS_TOKENIZER.src_lang = src_lang
    bos_token_id = TRANS_TOKENIZER.get_lang_id(tgt_lang)
    translated = []

    total_batches = (len(lines) + batch_size - 1) // batch_size

    for i in tqdm(range(0, len(lines), batch_size), total=total_batches,
                  desc="Translating", unit="batch", colour="green", dynamic_ncols=True):
        batch = lines[i: i + batch_size]
        encoded = TRANS_TOKENIZER(batch, return_tensors="pt", padding=True, truncation=True).to(DEVICE)
        outputs = TRANS_MODEL.generate(**encoded, forced_bos_token_id=bos_token_id, max_length=256)
        decoded = TRANS_TOKENIZER.batch_decode(outputs, skip_special_tokens=True)
        translated.extend(decoded)

    return translated
