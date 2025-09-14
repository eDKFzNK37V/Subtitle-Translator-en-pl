# pipeline.py
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import language_tool_python
from subtitle_workflow import translate_lines, model_setup
from resources import tool_pl, tool_en, ENHANCED_GLOSSARY, apply_context_sensitive_glossary
from text_tools import (
    correct_punctuation,
    correct_grammar_with_fallback,
    correct_punctuation_batch,
    correct_grammar_batch,
    clean_translation,
    extract_tags_with_placeholders,
    restore_tags_from_placeholders,
    detect_and_improve_formality,
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

# -----------------------------
# Single-line correction
# -----------------------------

def correct_text(text, lang):
    """
    Enhanced single-line correction with confidence-based fallback.
    """
    try:
        if lang.lower() == "pl":
            matches = _lt_check_with_timeout(tool_pl, _clamp(text), LT_TIMEOUT)
            if matches:
                text = language_tool_python.utils.correct(text, matches)
        elif lang.lower() == "en":
            # Grammar first with confidence fallback
            try:
                text = correct_grammar_with_fallback(_clamp(text), CONFIDENCE_THRESHOLD)
            except Exception:
                pass
            # Then LanguageTool (guarded)
            matches = _lt_check_with_timeout(tool_en, _clamp(text), LT_TIMEOUT)
            if matches:
                text = language_tool_python.utils.correct(text, matches)
        
        # Punctuation (guarded)
        try:
            text = correct_punctuation(_clamp(text), "kredor")
        except Exception:
            pass
            
        # Style/tone adjustment for subtitles with enhanced formality detection and quality fixes
        from text_tools import fix_common_translation_issues
        text = fix_common_translation_issues(text, lang)
        text = detect_and_improve_formality(text, lang)
        
        return clean_translation(text)
    except Exception:
        # Absolute fallback: do minimal cleanup and return
        return clean_translation(text)

# -----------------------------
# Batch correction (per-line guarded)
# -----------------------------


def correct_text_batch(lines, lang, progress_callback=None):
    """
    Minimalistic correction pipeline to prevent over-correction and quality degradation.
    Only applies essential corrections with maximum safety.
    """
    from text_tools import group_dialogue_lines, split_grouped_translations
    total = len(lines)
    lang_lower = lang.lower()

    # Group dialogue lines for context preservation
    grouped_lines, group_map = group_dialogue_lines(lines)

    # Ultra-conservative correction approach
    grouped_corrected = []
    for group in grouped_lines:
        # 1) Extract placeholders but skip heavy processing
        ph_map = []
        cleans = []
        for line in [group]:
            clean, ph = extract_tags_with_placeholders(line)
            ph_map.append(ph)
            cleans.append(clean)

        # 2) Skip grammar correction for now to prevent over-correction
        # This is the main source of Polish character loss and over-correction
        
        # 3) Skip punctuation restoration to avoid issues
        
        # 4) Skip LanguageTool to avoid over-correction
        
        # 5) Only apply minimal style fixes - the safest possible
        try:
            # Only apply absolutely essential fixes
            cleans = [fix_common_translation_issues(text, lang_lower) for text in cleans]
        except Exception:
            pass  # If anything fails, keep original

        # 6) Just clean and restore placeholders
        for i, t in enumerate(cleans):
            corrected = clean_translation(t)
            corrected = restore_tags_from_placeholders(corrected, ph_map[i])
            grouped_corrected.append(corrected)

    # Split grouped corrections back to original lines
    split_lines = split_grouped_translations(grouped_corrected, group_map)

    # Progress callback for each line
    if progress_callback:
        for idx in range(1, total + 1):
            progress_callback(idx, total)

    return split_lines


# -----------------------------
# Translation with context (unchanged except pre-extraction and safe restore)
# -----------------------------

def translate_with_context(lines, src_lang, tgt_lang, polish_only=False, translation_callback=None):
    """
    Translate lines with small context windows.
    - Preserves order and length.
    - Applies glossary pre-translation.
    - Respects polish_only flag.
    """
    model_setup()

    total = len(lines)
    result = []
    batch_size = 8
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

    # Pre-extract tags/placeholders for all lines (consistency with correction)
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

        trans_window = translate_lines(window, src_lang, tgt_lang, translation_callback=None)

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



