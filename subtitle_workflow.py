import os
from text_tools   import extract_tags, restore_tags
from pipeline     import correct_text_batch
from translate    import translate_batch
from utils        import load_subtitle_lines, save_subtitle_lines

def translate_subtitles(file_path, 
                        src_lang, 
                        tgt_lang,
                        polish_only=False,
                        translation_callback=None,
                        post_callback=None):
    # Load lines
    originals, subs = load_subtitle_lines(file_path)
    # Strip out tags for translation, store them for later restore
    tag_map = []
    if subs:
        stripped = []
        for ev in subs:
            clean, tags = extract_tags(ev.text)
            stripped.append(clean)
            tag_map.append(tags)
    else:
        stripped = originals
    # --- Stage 1: translation ---
    translated = translate_batch(
        stripped,
        src_lang,
        tgt_lang,
        progress_callback=translation_callback  # GUI: update_translation_progress
    )
    # --- Stage 2: correction/post-processing ---
    corrected_lines = correct_text_batch(
        translated,
        tgt_lang,
        progress_callback=post_callback         # GUI: update_post_progress
    )
    # Restore tags if there were any
    if tag_map:
        for i, corrected in enumerate(corrected_lines):
            corrected_lines[i] = restore_tags(corrected, tag_map[i])
            subs[i].text = corrected_lines[i]

    # Save to file
    ext = file_path.split('.')[-1].lower()
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.{ext}"
    save_subtitle_lines(corrected_lines, output_path, subs)

    return output_path, originals, corrected_lines