import os
import pysubs2
from text_tools import extract_tags, restore_tags, clean_translation
from pipeline import correct_text
from translate import translate_batch
from utils import format_ass
from utils import load_subtitle_lines



def translate_subtitles(file_path, src_lang, tgt_lang, polish_only=False):
    originals, subs = load_subtitle_lines(file_path)
    tag_map = []

    # Extract tags only if subs exist (ASS/SRT)
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
    log_path = os.path.splitext(file_path)[0] + "_log.txt"
    with open(log_path, "w", encoding="utf-8") as log_file:
        for i, line in enumerate(translated_lines):
            translated = clean_translation(line)
            corrected = correct_text(translated, tgt_lang)
            if tag_map:
                corrected = restore_tags(corrected, tag_map[i])
                subs[i].text = corrected
            corrected_lines.append(corrected)
            log_file.write(f"Original:   {originals[i]}\n")
            log_file.write(f"Translated: {translated}\n")
            log_file.write(f"Corrected:  {corrected}\n\n")

    ext = file_path.split('.')[-1].lower()
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.{ext}"
    save_subtitle_lines(corrected_lines, output_path, subs)
    return output_path, originals, corrected_lines



#def load_subtitle_lines(file_path):
    ext = file_path.split('.')[-1].lower()
    if ext in ["ass", "srt"]:
        subs = pysubs2.load(file_path, encoding="utf-8")
        return [event.text for event in subs], subs
    elif ext == "txt":
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
        return lines, None
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

#def save_subtitle_lines(lines, file_path, subs=None):
    ext = file_path.split('.')[-1].lower()
    if ext in ["ass", "srt"] and subs:
        for i, line in enumerate(lines):
            subs[i].text = line.strip()
        subs.save(file_path, encoding="utf-8", format=ext)
    elif ext == "txt":
        with open(file_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line.strip() + "\n")
    else:
        raise ValueError(f"Unsupported file format: .{ext}")


def create_comparison_subs(original_lines, corrected_lines, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for orig, corr in zip(original_lines, corrected_lines):
            f.write(f"{format_ass(orig, style='italic')}\n")
            f.write(f"{format_ass(corr, style='bold')}\n")

