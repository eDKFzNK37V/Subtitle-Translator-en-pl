# pipeline.py
import re
import threading
import language_tool_python
from subtitle_workflow import model_setup
from resources import tool_pl, tool_en, ENHANCED_GLOSSARY, apply_context_sensitive_glossary
from text_tools import (
    correct_grammar_with_fallback,
    clean_translation,
    extract_tags_with_placeholders,
    restore_tags_from_placeholders,
)

GLOSSARY = ENHANCED_GLOSSARY

# -----------------------------
# Safety helpers to prevent hangs
# -----------------------------

MAX_CHARS_FOR_MODELS = 800
LT_TIMEOUT = 1.2          # Reduced timeout for faster processing
MAX_WORKERS_LT = 6        # Optimized LT parallelism
CORR_BATCH_SIZE = 24      # Optimized correction batch size
CONFIDENCE_THRESHOLD = 0.90  # Very high confidence threshold to prevent over-correction

def _clamp(text: str, max_chars: int = MAX_CHARS_FOR_MODELS) -> str:
    return text if len(text) <= max_chars else text[:max_chars]

def _lt_check_with_timeout(tool, text: str, timeout_sec: float):
    holder = {"res": [], "err": None}
    def run():
        try:
            holder["res"] = tool.check(text)
        except Exception as e:
            holder["err"] = e
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout_sec)
    if t.is_alive() or holder["err"] is not None:
        return []
    return holder["res"]


# -----------------------------
# Enhanced Glossary with context awareness
# -----------------------------

def apply_glossary(text: str, glossary=None, use_context=True) -> str:
    """
    Apply glossary with enhanced context awareness and better term matching.
    """
    glossary = glossary or GLOSSARY
    result = text
    
    # Apply standard glossary
    for src, tgt in glossary.items():
        result = re.sub(rf"\b{re.escape(src)}\b", tgt, result, flags=re.IGNORECASE)
    
    # Apply context-sensitive glossary if enabled
    if use_context:
        result = apply_context_sensitive_glossary(result)
    
    return result



