import os
import time
from text_tools   import extract_tags, restore_tags, clean_translation
from pipeline     import correct_text_batch
from translate    import translate_batch
from utils        import format_ass, load_subtitle_lines, save_subtitle_lines

def translate_subtitles(
    file_path,
    src_lang,
    tgt_lang,
    polish_only=False,
    progress_callback=None
):
    originals, subs = load_subtitle_lines(file_path)

    # strip tags
    tag_map = []
    if subs:
        stripped = []
        for ev in subs:
            clean, tags = extract_tags(ev.text)
            stripped.append(clean)
            tag_map.append(tags)
    else:
        stripped = originals

    # translate or skip
    translated = (
        stripped if polish_only
        else translate_batch(stripped, src_lang, tgt_lang)
    )

    # Use batch correction
    corrected_lines = correct_text_batch(translated, tgt_lang, progress_callback=progress_callback)

    # Restore tags if needed
    if tag_map:
        for i, corrected in enumerate(corrected_lines):
            corrected_lines[i] = restore_tags(corrected, tag_map[i])
            subs[i].text = corrected_lines[i]

    ext = file_path.split('.')[-1].lower()
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.{ext}"
    save_subtitle_lines(corrected_lines, output_path, subs)
    return output_path, originals, corrected_lines


def create_comparison_subs(original_lines, corrected_lines, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        for orig, corr in zip(original_lines, corrected_lines):
            f.write(format_ass(orig,   style="italic") + "\n")
            f.write(format_ass(corr,   style="bold")   + "\n")