import torch
from transformers import (
    AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForTokenClassification,
)
from config import DEVICE
# Grammar correction model

GRAMMAR_MODEL = AutoModelForSeq2SeqLM.from_pretrained(
    "prithivida/grammar_error_correcter_v1"
).to(DEVICE)
GRAMMAR_MODEL.eval()

GRAMMAR_TOKENIZER = AutoTokenizer.from_pretrained(
    "prithivida/grammar_error_correcter_v1"
)

# Punctuation models
PUNCT_MODELS = {
    "kredor": AutoModelForTokenClassification.from_pretrained(
        "kredor/punctuate-all"
    ).to(DEVICE),
    "oliverguhr": AutoModelForTokenClassification.from_pretrained(
        "oliverguhr/fullstop-punctuation-multilang-large"
    ).to(DEVICE),
}
for _m in PUNCT_MODELS.values():
    _m.eval()


PUNCT_TOKENIZERS = {
    "kredor": AutoTokenizer.from_pretrained("kredor/punctuate-all"),
    "oliverguhr": AutoTokenizer.from_pretrained(
        "oliverguhr/fullstop-punctuation-multilang-large"
    ),
}

# NLLB-200-1.3B model and tokenizer (preloaded as globals)
NLLB_MODEL_NAME = "facebook/nllb-200-1.3B"
NLLB_BEAMS = 5  # Optimized beam count for performance balance
NLLB_BATCH_SIZE = 12  # Optimized batch size for memory efficiency
NLLB_DTYPE = torch.float16 if torch.cuda.is_available() else None
NLLB_TOKENIZER = AutoTokenizer.from_pretrained(NLLB_MODEL_NAME)
NLLB_MODEL = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL_NAME, torch_dtype=NLLB_DTYPE).to(DEVICE)
NLLB_MODEL.eval()

def get_nllb_globals():
    """Return the pre-loaded global NLLB model instances for efficiency."""
    return NLLB_MODEL, NLLB_TOKENIZER, DEVICE

