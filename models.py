from transformers import (
    M2M100ForConditionalGeneration,
    M2M100Tokenizer,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForTokenClassification
)
from config import DEVICE

print("Loading translation model...")
TRANS_MODEL = M2M100ForConditionalGeneration.from_pretrained(
    "facebook/m2m100_418M"
).to(DEVICE)
TRANS_TOKENIZER = M2M100Tokenizer.from_pretrained("facebook/m2m100_418M")

print("Loading grammar correction model...")
GRAMMAR_MODEL = AutoModelForSeq2SeqLM.from_pretrained(
    "prithivida/grammar_error_correcter_v1"
).to(DEVICE)
GRAMMAR_TOKENIZER = AutoTokenizer.from_pretrained(
    "prithivida/grammar_error_correcter_v1"
)

print("Loading punctuation models...")
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
