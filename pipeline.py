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
    apply_style_tone_batch,
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
CONFIDENCE_THRESHOLD = 0.80  # Increased confidence threshold for better protection

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
    Enhanced context-aware correction with confidence-based fallback and style adjustment.
    """
    from text_tools import group_dialogue_lines, split_grouped_translations
    total = len(lines)
    lang_lower = lang.lower()
    use_lt = lang_lower in ("pl", "en")
    lt_tool = tool_pl if lang_lower == "pl" else (tool_en if lang_lower == "en" else None)

    # Group dialogue lines for context-aware correction
    grouped_lines, group_map = group_dialogue_lines(lines)

    # Enhanced correction pipeline with new order and confidence checks
    grouped_corrected = []
    for group in grouped_lines:
        # 1) Placeholders + enhanced glossary with context
        ph_map = []
        cleans = []
        for line in [group]:
            clean, ph = extract_tags_with_placeholders(line)
            ph_map.append(ph)
            # Apply enhanced glossary with context awareness
            clean = apply_glossary(clean, use_context=True)
            cleans.append(clean)

        # 2) Neural grammar correction with confidence-based fallback
        try:
            cleans = correct_grammar_batch([_clamp(t) for t in cleans], CONFIDENCE_THRESHOLD)
        except Exception:
            tmp = []
            for t in cleans:
                try:
                    tmp.append(correct_grammar_with_fallback(_clamp(t), CONFIDENCE_THRESHOLD))
                except Exception:
                    tmp.append(t)
            cleans = tmp

        # 3) Punctuation restoration (batched)
        try:
            cleans = correct_punctuation_batch([_clamp(t) for t in cleans], "kredor")
        except Exception:
            tmp = []
            for t in cleans:
                try:
                    tmp.append(correct_punctuation(_clamp(t), "kredor"))
                except Exception:
                    tmp.append(t)
            cleans = tmp

        # 4) LanguageTool correction (parallel per line, short timeout, skip long lines)
        if use_lt and lt_tool is not None:
            def lt_fix(t):
                t_short = _clamp(t)
                matches = _lt_check_with_timeout(lt_tool, t_short, LT_TIMEOUT)
                if matches:
                    try:
                        return language_tool_python.utils.correct(t, matches)
                    except Exception:
                        return t
                return t
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_LT) as ex:
                cleans = list(ex.map(lt_fix, cleans))

        # 5) Conservative style/tone adjustment with quality fixes for subtitle context
        try:
            # Apply only essential quality improvements to prevent over-correction
            from text_tools import fix_common_translation_issues
            # Only apply style fixes if text is clearly problematic
            original_length = sum(len(text) for text in cleans)
            cleans = [fix_common_translation_issues(text, lang_lower) for text in cleans]
            
            # Check for excessive changes and revert if too many
            corrected_length = sum(len(text) for text in cleans)
            if abs(original_length - corrected_length) / max(original_length, 1) > 0.3:
                # Too many changes, revert to safer corrections
                cleans = [detect_and_improve_formality(text, lang_lower) for text in cleans]
        except Exception:
            # Fallback to basic style adjustment
            try:
                cleans = apply_style_tone_batch(cleans, lang_lower)
            except Exception:
                pass  # If style adjustment fails, continue with existing text

        # 6) Final clean + restore placeholders
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



