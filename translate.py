from tqdm import tqdm
from config import DEVICE
from models import TRANS_MODEL, TRANS_TOKENIZER

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
