import os
import pysubs2
from text_tools import extract_tags, restore_tags, clean_translation
from pipeline import correct_text
from translate import translate_batch

def translate_subtitles(file_path, src_lang, tgt_lang, polish_only=False):
    subs = pysubs2.load(file_path, encoding="utf-8")
    originals = []
    tag_map = []
    for event in subs:
        clean, tags = extract_tags(event.text)
        originals.append(clean)
        tag_map.append(tags)
    if polish_only:
        translated_lines = originals
    else:
        translated_lines = translate_batch(originals, src_lang, tgt_lang)
    log_path = os.path.splitext(file_path)[0] + "_log.txt"
    with open(log_path, "w", encoding="utf-8") as log_file:
        for i, event in enumerate(subs):
            translated = clean_translation(translated_lines[i])
            corrected = correct_text(translated, tgt_lang)
            event.text = restore_tags(corrected, tag_map[i])
            log_file.write(f"Original:   {originals[i]}\n")
            log_file.write(f"Translated: {translated}\n")
            log_file.write(f"Corrected:  {corrected}\n\n")
    output_path = os.path.splitext(file_path)[0] + f"_{tgt_lang}.ass"
    subs.save(output_path, encoding="utf-8")
    return output_path