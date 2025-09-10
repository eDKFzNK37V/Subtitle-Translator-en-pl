import torch
from transformers import (
    M2M100ForConditionalGeneration, M2M100Tokenizer,
    AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForTokenClassification,
)
from config import DEVICE

# Translation model loader
def get_m2m100_model(model_name="facebook/m2m100_418M"):
    tokenizer = M2M100Tokenizer.from_pretrained(model_name)
    model = M2M100ForConditionalGeneration.from_pretrained(model_name)
    model = model.to(DEVICE)  # type: ignore
    model.eval()              # inference mode
    return model, tokenizer
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
NLLB_BEAMS = 6
NLLB_BATCH_SIZE = 16
NLLB_DTYPE = torch.float16 if torch.cuda.is_available() else None
NLLB_TOKENIZER = AutoTokenizer.from_pretrained(NLLB_MODEL_NAME)
NLLB_MODEL = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL_NAME, torch_dtype=NLLB_DTYPE).to(DEVICE)
NLLB_MODEL.eval()

def get_nllb_globals():
    model_name = "facebook/nllb-200-1.3B"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, torch_dtype=dtype).to(device).eval()
    return model, tokenizer, device

def get_translation_model():
    model_name = "facebook/m2m100_418M"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to("cuda" if torch.cuda.is_available() else "cpu")
    return model, tokenizer

