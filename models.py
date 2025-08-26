import torch
from transformers import (
    M2M100ForConditionalGeneration, M2M100Tokenizer,
    AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForTokenClassification
)
from config import DEVICE

# Translation model loader
def get_translation_model(model_name="facebook/m2m100_418M"):
    tokenizer = M2M100Tokenizer.from_pretrained(model_name)
    model = M2M100ForConditionalGeneration.from_pretrained(model_name)
    model = model.to(DEVICE)  # type: ignore
    return model, tokenizer

# Grammar correction model
GRAMMAR_MODEL = AutoModelForSeq2SeqLM.from_pretrained(
    "prithivida/grammar_error_correcter_v1"
).to(DEVICE)
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
PUNCT_TOKENIZERS = {
    "kredor": AutoTokenizer.from_pretrained("kredor/punctuate-all"),
    "oliverguhr": AutoTokenizer.from_pretrained(
        "oliverguhr/fullstop-punctuation-multilang-large"
    ),
}
