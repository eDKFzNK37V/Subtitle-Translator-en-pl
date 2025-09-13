# pipeline.py
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import language_tool_python
from subtitle_workflow import translate_lines, model_setup, translate_lines_nllb
from resources import tool_pl, tool_en
from text_tools import (
    correct_punctuation,
    correct_grammar,
    correct_punctuation_batch,
    correct_grammar_batch,
    clean_translation,
    extract_tags_with_placeholders,
    restore_tags_from_placeholders,
)

GLOSSARY = {
    "White Hearts": "Białe Serca",
    "savior": "zbawiciel",
    "Hero": "Bohater",
}

# -----------------------------
# Safety helpers to prevent hangs
# -----------------------------

MAX_CHARS_FOR_MODELS = 800
LT_TIMEOUT = 1.5          # seconds per line
MAX_WORKERS_LT = 4        # LT parallelism
CORR_BATCH_SIZE = 32      # correction batch size

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
# Glossary
# -----------------------------

def apply_glossary(text: str, glossary=None) -> str:
    glossary = glossary or GLOSSARY
    for src, tgt in glossary.items():
        text = re.sub(rf"\b{re.escape(src)}\b", tgt, text, flags=re.IGNORECASE)
    return text

# -----------------------------
# Single-line correction
# -----------------------------

def correct_text(text, lang):
    try:
        if lang.lower() == "pl":
            matches = _lt_check_with_timeout(tool_pl, _clamp(text), LT_TIMEOUT)
            if matches:
                text = language_tool_python.utils.correct(text, matches)
        elif lang.lower() == "en":
            # Grammar first (guarded)
            try:
                text = correct_grammar(_clamp(text))
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
        return clean_translation(text)
    except Exception:
        # Absolute fallback: do minimal cleanup and return
        return clean_translation(text)

# -----------------------------
# Batch correction (per-line guarded)
# -----------------------------

def correct_text_batch(lines, lang, progress_callback=None):
    total = len(lines)
    out = ["" for _ in range(total)]
    lang_lower = lang.lower()
    use_lt = lang_lower in ("pl", "en")
    lt_tool = tool_pl if lang_lower == "pl" else (tool_en if lang_lower == "en" else None)

    for start in range(0, total, CORR_BATCH_SIZE):
        end = min(start + CORR_BATCH_SIZE, total)
        batch = lines[start:end]

        # 1) Placeholders + glossary
        ph_maps = []
        cleans = []
        for line in batch:
            clean, ph_map = extract_tags_with_placeholders(line)
            ph_maps.append(ph_map)
            # optional glossary
            for src, tgt in GLOSSARY.items():
                clean = re.sub(rf"\b{re.escape(src)}\b", tgt, clean, flags=re.IGNORECASE)
            cleans.append(clean)

        # 2) Grammar (batched where beneficial)
        if lang_lower == "en":
            try:
                cleans = correct_grammar_batch([_clamp(t) for t in cleans])
            except Exception:
                # fallback: per-line guarded
                tmp = []
                for t in cleans:
                    try:
                        tmp.append(correct_grammar(_clamp(t)))
                    except Exception:
                        tmp.append(t)
                cleans = tmp

        # 3) LanguageTool (parallel per line, short timeout, skip long lines)
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

        # 4) Punctuation (batched)
        try:
            cleans = correct_punctuation_batch([_clamp(t) for t in cleans], "kredor")
        except Exception:
            # fallback single-line punctuation if needed
            tmp = []
            for t in cleans:
                try:
                    tmp.append(correct_punctuation(_clamp(t), "kredor"))
                except Exception:
                    tmp.append(t)
            cleans = tmp

        # 5) Final clean + restore placeholders
        for i, t in enumerate(cleans):
            corrected = clean_translation(t)
            corrected = restore_tags_from_placeholders(corrected, ph_maps[i])
            out[start + i] = corrected
            if progress_callback:
                progress_callback(start + i + 1, total)

    return out


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



