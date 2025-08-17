import os
from text_tools import extract_tags, restore_tags, clean_translation
from pipeline import correct_text
from translate import translate_batch
from utils import format_ass, load_subtitle_lines, save_subtitle_lines

def translate_subtitles(file_path, src_lang, tgt_lang, polish_only=False):
    originals, subs = load_subtitle_lines(file_path)
    tag_map = []

    if subs:
        stripped_lines = []
        for event in subs:
            clean, tags = extract_tags(event.text)
            stripped_lines.append(clean)
            tag_map.append(tags)
    else:
        stripped_lines = originals

    translated_lines = stripped_lines if polish_only else translate_batch(stripped_lines, src_lang, tgt_lang)
    corrected_lines = []

    for i, line in enumerate(translated_lines):
        translated = clean_translation(line)
        corrected = correct_text(translated, tgt_lang)
        if tag_map:
            corrected = restore_tags(corrected, tag_map[i])
            subs[i].text = corrected
        corrected_lines.append(corrected)

    ext = file_path.split('.')[-1].lower()
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.{ext}"
    save_subtitle_lines(corrected_lines, output_path, subs)
    return output_path, originals, corrected_lines

def create_comparison_subs(original_lines, corrected_lines, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for orig, corr in zip(original_lines, corrected_lines):
            f.write(f"{format_ass(orig, style='italic')}\n")
            f.write(f"{format_ass(corr, style='bold')}\n")
