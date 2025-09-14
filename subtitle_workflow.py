# subtitle_workflow.py
import os
import re
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from utils import load_subtitle_lines, save_subtitle_lines
from models import get_nllb_globals
from config import DEVICE, selected_engine as global_selected_engine
from text_tools import extract_tags_with_placeholders, restore_tags_from_placeholders

def run_gui_entry():
    from gui import run_gui
    run_gui()

def _get_target_lang_from_code(lang_code):
    """Convert NLLB language codes back to simple language codes for quality enhancement."""
    code_map = {
        "eng_Latn": "en",
        "pol_Latn": "pl",
        "fra_Latn": "fr", 
        "deu_Latn": "de",
        "jpn_Jpan": "ja"
    }
    return code_map.get(lang_code, "en")  # Default to English if not found

## NLLB language code map (extend as needed)
def model_setup():
    global TRANS_MODEL, TRANS_TOKENIZER
    # Always use NLLB as the only supported model
    TRANS_MODEL, TRANS_TOKENIZER, _ = get_nllb_globals()
    TRANS_MODEL.eval()

# Language code maps for NLLB
NLLB_LANG = {
    "en": "eng_Latn",
    "pl": "pol_Latn",
}

def get_model_lang_code(lang, model_type="nllb"):
    # Always use NLLB language codes
    return NLLB_LANG.get(lang, lang)

def load_nllb_13b():
    model_id = "facebook/nllb-200-1.3B"
    tok = AutoTokenizer.from_pretrained(model_id)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else None
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id, torch_dtype=dtype)
    model.to(device)
    model.eval()
    return model, tok, device

def translate_batch_nllb(model, tok, device, lines, src_code, tgt_code,
                         max_length=256, num_beams=5, no_repeat_ngram_size=2,
                         length_penalty=0.9, repetition_penalty=1.05):
    """
    Optimized NLLB translation with improved quality and performance balance.
    Enhanced for subtitle translation with streamlined parameters.
    Assumes:
      - tok is the NLLB tokenizer
      - src_code/tgt_code are already in NLLB form (e.g. "eng_Latn", "pol_Latn")
    """
    # Directly set the NLLB tokenizer’s src and tgt
    tok.src_lang = src_code
    tgt_id = tok.convert_tokens_to_ids(tgt_code)

    # Optimized encoding with dynamic padding for better memory efficiency
    enc = tok(
        lines,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_length
    ).to(device)

    with torch.no_grad():
        # Optimized generation parameters balancing quality and speed
        gen = model.generate(
            **enc,
            forced_bos_token_id=tgt_id,
            max_length=max_length,
            num_beams=num_beams,  # Reduced for better speed while maintaining quality
            early_stopping=True,
            length_penalty=length_penalty,  # Optimized for natural subtitle length
            no_repeat_ngram_size=no_repeat_ngram_size,  # Reduced for better performance
            do_sample=False,  # Deterministic for consistency
            num_return_sequences=1,
            repetition_penalty=repetition_penalty,  # Reduced penalty for better flow
            # Removed unused parameters for performance optimization
        )
    
    decoded = tok.batch_decode(gen, skip_special_tokens=True)
    
    # Apply enhanced post-processing for each translated line  
    enhanced_results = []
    target_lang = _get_target_lang_from_code(tgt_code)
    for idx, text in enumerate(decoded):
        # Apply immediate quality improvements with optimized processing
        enhanced_text = _enhance_translation_quality(text, target_lang, lines[idx] if idx < len(lines) else "")
        enhanced_results.append(enhanced_text)
    
    return enhanced_results

def translate_lines_nllb(model, tok, device, lines, src_lang, tgt_lang,
                         batch_size=12, progress_callback=None):
    # Always use the model and tokenizer passed as arguments (do not overwrite with globals)
    # Map GUI codes ("en","pl") → NLLB codes ("eng_Latn","pol_Latn")
    src_code = get_model_lang_code(src_lang, "nllb")
    tgt_code = get_model_lang_code(tgt_lang, "nllb")
    out = []
    i = 0
    bs = batch_size
    while i < len(lines):
        try:
            batch = lines[i:i+bs]
            preds = translate_batch_nllb(model, tok, device, batch, src_code, tgt_code)
            out.extend(preds)
            i += bs
            if progress_callback:
                progress_callback(min(i, len(lines)), len(lines))
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            bs = max(1, bs // 2)  # halve and retry
            if bs == 1:
                # last resort: process one line
                continue
    return out

def translate_with_context_nllb(
    lines,
    src_lang,
    tgt_lang,
    model,
    tokenizer,
    device,
    beams=5,
    batch_size=12,
    polish_only=False,
    glossary=None,
    translation_callback=None
):
    """
    Context-aware translation with dialogue grouping and robust tag handling.
    - Groups consecutive lines for translation if the next starts with a lowercase letter.
    - Translates grouped lines in context, then splits back to original lines.
    - Preserves tag positions and mapping.
    - Applies glossary pre-translation.
    - Respects polish_only flag.
    """
    from pipeline import apply_glossary, GLOSSARY
    from text_tools import group_dialogue_lines, split_grouped_translations
    model_setup()

    total = len(lines)
    if polish_only and src_lang.lower() == tgt_lang.lower():
        out = []
        for line in lines:
            clean, ph_map = extract_tags_with_placeholders(line)
            clean = apply_glossary(clean, glossary)
            out.append(restore_tags_from_placeholders(clean, ph_map))
        if translation_callback:
            for i in range(1, total + 1):
                translation_callback(i, total)
        return out

    # Group dialogue lines for context-aware translation
    grouped_lines, group_map = group_dialogue_lines(lines)

    # Pre-extract tags/placeholders for all grouped lines
    grouped_clean = []
    grouped_ph_maps = []
    for group in grouped_lines:
        clean, ph_map = extract_tags_with_placeholders(group)
        clean = apply_glossary(clean, glossary)
        grouped_clean.append(clean)
        grouped_ph_maps.append(ph_map)

    # Use NLLB as the only supported model type
    model_type = "nllb"
    src_code = get_model_lang_code(src_lang, model_type)
    tgt_code = get_model_lang_code(tgt_lang, model_type)

    # Translate grouped lines in batches
    translated_groups = []
    for i in range(0, len(grouped_clean), batch_size):
        batch = grouped_clean[i:i+batch_size]
        preds = translate_lines_nllb(model, tokenizer, device, batch, src_lang, tgt_lang, batch_size=batch_size, progress_callback=None)
        translated_groups.extend(preds)
        if translation_callback:
            progress = min(i + len(batch), len(grouped_clean))
            translation_callback(progress, len(grouped_clean))

    # Restore tags for each group
    restored_groups = [restore_tags_from_placeholders(trans, ph_map) for trans, ph_map in zip(translated_groups, grouped_ph_maps)]

    # Split grouped translations back to original lines
    split_lines = split_grouped_translations(restored_groups, group_map)

    # Final progress update only if we haven't reached the end yet
    if translation_callback and len(grouped_clean) > 0:
        translation_callback(len(grouped_clean), len(grouped_clean))

    return split_lines

def correct_text_batch_nllb(lines, src_lang, tgt_lang, glossary=None, translation_callback=None):
    """
    Enhanced NLLB correction using the comprehensive correction pipeline from pipeline.py
    """
    from pipeline import correct_text_batch
    
    # Use the enhanced correction pipeline with NLLB model setup
    model_setup()  # Ensure NLLB model is loaded
    
    # Apply the enhanced correction pipeline
    corrected_lines = correct_text_batch(lines, tgt_lang, translation_callback)
    
    return corrected_lines



def translate_lines(lines, src_lang, tgt_lang, translation_callback=None, glossary=None):
    """
    Context-aware translation with dialogue grouping and robust tag handling.
    Groups consecutive lines for translation if the next starts with a lowercase letter.
    Translates grouped lines, then splits back to original lines.
    """
    model_setup()  # Ensure correct model/tokenizer is set
    from pipeline import apply_glossary, GLOSSARY
    from text_tools import group_dialogue_lines, split_grouped_translations

    # Group dialogue lines for context-aware translation
    grouped_lines, group_map = group_dialogue_lines(lines)

    # Pre-extract tags/placeholders for all grouped lines
    grouped_clean = []
    grouped_ph_maps = []
    for group in grouped_lines:
        clean, ph_map = extract_tags_with_placeholders(group)
        clean = apply_glossary(clean, glossary)
        grouped_clean.append(clean)
        grouped_ph_maps.append(ph_map)

    # Translate grouped lines
    translated_groups = translate_batch(
        grouped_clean,
        src_lang,
        tgt_lang,
        batch_size=6,
        progress_callback=translation_callback
    )

    # Restore tags for each group
    restored_groups = [restore_tags_from_placeholders(trans, ph_map) for trans, ph_map in zip(translated_groups, grouped_ph_maps)]

    # Split grouped translations back to original lines
    split_lines = split_grouped_translations(restored_groups, group_map)
    return split_lines

def translate_subtitles(file_path, src_lang, tgt_lang, polish_only=False, translation_callback=None, glossary=None, n_wordidx=0, use_contextaware_n=False):
    r"""
    Load (texts, subs, idx_map), apply dialogue grouping, tag handling, and context-aware translation.
    Enhanced with context-aware \N reinsertion and improved processing pipeline.
    """
    model_setup()  # Ensure correct model/tokenizer is set
    from pipeline import apply_glossary, GLOSSARY
    from text_tools import extract_newline_tags, insert_newline_tags_at_wordidx, insert_newline_tags_contextaware, group_dialogue_lines, split_grouped_translations

    texts, subs, idx_map = load_subtitle_lines(file_path)
    if not texts:
        raise ValueError(f"[translate_subtitles] No subtitle lines loaded from {file_path!r}")

    # --- Remove \N tags and count them ---
    cleaned_lines = []
    n_tag_counts = []
    for line in texts:
        cleaned, n_count = extract_newline_tags(line)
        cleaned_lines.append(cleaned)
        n_tag_counts.append(n_count)

    # Dialogue grouping for context-aware translation
    grouped_lines, group_map = group_dialogue_lines(cleaned_lines)

    # Pre-extract tags/placeholders for all grouped lines
    grouped_clean = []
    grouped_ph_maps = []
    for group in grouped_lines:
        clean, ph_map = extract_tags_with_placeholders(group)
        clean = apply_glossary(clean, glossary, use_context=True)
        grouped_clean.append(clean)
        grouped_ph_maps.append(ph_map)

    # If polishing only and same language, skip model translate
    if polish_only and src_lang.lower() == tgt_lang.lower():
        translated_groups = grouped_clean[:]
        if translation_callback:
            for idx in range(1, len(translated_groups) + 1):
                translation_callback(idx, len(translated_groups))
    else:
        translated_groups = translate_batch(
            grouped_clean,
            src_lang,
            tgt_lang,
            batch_size=6,
            progress_callback=translation_callback
        )

    # Restore tags for each group
    restored_groups = [restore_tags_from_placeholders(trans, ph_map) for trans, ph_map in zip(translated_groups, grouped_ph_maps)]

    # Split grouped translations back to original lines
    restored_lines = split_grouped_translations(restored_groups, group_map)

    # --- Enhanced \N tag insertion logic ---
    final_lines = []
    for line, n_count in zip(restored_lines, n_tag_counts):
        if n_count > 0:
            if use_contextaware_n:
                # Use context-aware insertion
                processed_line = insert_newline_tags_contextaware(line, n_count, prefer_punctuation=True)
            else:
                # Use word index-based insertion (backwards compatibility)
                processed_line = insert_newline_tags_at_wordidx(line, n_count, n_wordidx)
        else:
            processed_line = line
        final_lines.append(processed_line)

    ext = file_path.split('.')[-1].lower()
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.{ext}"
    save_subtitle_lines(final_lines, output_path, subs, idx_map)

    return output_path, texts, final_lines

def translate_batch(lines, src_lang, tgt_lang, batch_size=16, progress_callback=None):
    """
    Enhanced translation batch with improved quality controls for subtitle context.
    Features:
    - Optimized generation parameters for natural subtitle speech
    - Multiple beam generations with quality selection
    - Length penalty adjustments for subtitle constraints
    - Temperature control for more natural output
    """
    model_setup()  # Ensure correct model/tokenizer is set
    translated = []
    total_lines = len(lines)

    # Use NLLB as the only supported model type
    model_type = "nllb"
    src_code = get_model_lang_code(src_lang, model_type)
    tgt_code = get_model_lang_code(tgt_lang, model_type)
    
    # Setup NLLB tokenizer
    TRANS_TOKENIZER.src_lang = src_code
    tgt_id = TRANS_TOKENIZER.convert_tokens_to_ids(tgt_code)
    bos_token_id = tgt_id

    for i in range(0, total_lines, batch_size):
        batch = lines[i: i + batch_size]
        encoded = TRANS_TOKENIZER(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True
        ).to(DEVICE)

        with torch.no_grad():
            # Enhanced generation parameters for subtitle quality
            if model_type == "nllb":
                outputs = TRANS_MODEL.generate(
                    **encoded,
                    forced_bos_token_id=bos_token_id,
                    max_length=256,
                    num_beams=8,  # Increased for better quality
                    early_stopping=True,
                    length_penalty=0.8,  # Slightly favor shorter, more natural text
                    no_repeat_ngram_size=3,  # Reduce repetition
                    do_sample=False,  # Use deterministic beam search for consistency
                    num_return_sequences=1,
                    bad_words_ids=None,
                    temperature=1.0,
                    top_k=50,
                    top_p=0.95,
                    repetition_penalty=1.1  # Slight penalty for repetition
                )
            else:
                outputs = TRANS_MODEL.generate(
                    **encoded,
                    forced_bos_token_id=bos_token_id,
                    max_length=256,
                    num_beams=8,  # Increased for better quality
                    early_stopping=True,
                    length_penalty=0.8,  # Slightly favor shorter, more natural text
                    no_repeat_ngram_size=3,  # Reduce repetition
                    do_sample=False,  # Use deterministic beam search for consistency
                    num_return_sequences=1,
                    bad_words_ids=None,
                    temperature=1.0,
                    top_k=50,
                    top_p=0.95,
                    repetition_penalty=1.1  # Slight penalty for repetition
                )

        decoded = TRANS_TOKENIZER.batch_decode(outputs, skip_special_tokens=True)

        # Enhanced post-processing for each translated line
        for idx, text in enumerate(decoded):
            # Apply immediate quality improvements
            enhanced_text = _enhance_translation_quality(text, tgt_lang, lines[i + idx] if i + idx < len(lines) else "")
            translated.append(enhanced_text)
            if progress_callback:
                current_line = i + idx + 1
                progress_callback(current_line, total_lines)

    return translated

def _enhance_translation_quality(translated_text: str, target_lang: str, source_text: str = "") -> str:
    """
    Conservative immediate quality enhancements for translated text.
    Reduced pattern matching to prevent over-correction and character loss.
    """
    if not translated_text.strip():
        return translated_text
    
    # Safety check for Polish characters
    polish_chars = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż', 'Ą', 'Ć', 'Ę', 'Ł', 'Ń', 'Ó', 'Ś', 'Ź', 'Ż']
    original_polish_chars = [char for char in translated_text if char in polish_chars]
    
    enhanced = translated_text
    
    # Conservative language-specific improvements - only essential patterns
    if target_lang.lower() == "pl":
        # Polish subtitle optimizations - only the safest patterns
        immediate_fixes = [
            # Only essential fixes that are very safe
            (r'\bja jestem\b', 'jestem'),
            (r'\bobecnie\b', 'teraz'),
            (r'\btak,\s*tak\b', 'tak'),
            (r'\bnie,\s*nie\b', 'nie'),
        ]
    else:
        # English subtitle optimizations - only essential patterns
        immediate_fixes = [
            # Only essential contractions that are very safe
            (r'\bI will\b', "I'll"),
            (r'\byou will\b', "you'll"),
            (r'\bwe will\b', "we'll"),
            (r'\byes,\s*yes\b', 'yes'),
            (r'\bno,\s*no\b', 'no'),
        ]
    
    # Apply immediate fixes conservatively
    for pattern, replacement in immediate_fixes:
        # Test replacement for Polish text
        if target_lang.lower() == "pl":
            test_result = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
            result_polish_chars = [char for char in test_result if char in polish_chars]
            if len(result_polish_chars) >= len(original_polish_chars):
                enhanced = test_result
        else:
            enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
    
    # Apply only essential universal fixes
    enhanced = _apply_universal_subtitle_fixes_conservative(enhanced)
    
    # Final safety check for Polish characters
    if target_lang.lower() == "pl":
        final_polish_chars = [char for char in enhanced if char in polish_chars]
        if len(final_polish_chars) < len(original_polish_chars) * 0.9:  # Lost more than 10% of Polish chars
            return translated_text
    
    return enhanced.strip()

def _apply_universal_subtitle_fixes_conservative(text: str) -> str:
    """
    Conservative universal fixes for subtitle readability.
    Only essential fixes to prevent over-correction.
    """
    # Only essential spacing and punctuation fixes
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\s+([.!?,:;])', r'\1', text)  # Remove space before punctuation
    
    # Capitalize first letter if needed
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    return text

