# pipeline.py
import language_tool_python
from text_tools import correct_punctuation, correct_grammar, clean_translation
from resources import tool_pl, tool_en

def correct_text(text, lang):
    if lang.lower() == "pl":
        matches = tool_pl.check(text)
        text = language_tool_python.utils.correct(text, matches)
    elif lang.lower() == "en":
        text = correct_grammar(text)
        matches = tool_en.check(text)
        text = language_tool_python.utils.correct(text, matches)
    text = correct_punctuation(text, "kredor")
    return clean_translation(text)

def correct_text_batch(lines, lang, progress_callback=None):
    total = len(lines)
    result = []
    lang_lower = lang.lower()
    for idx, line in enumerate(lines):
        if lang_lower == "pl":
            matches = tool_pl.check(line)
            line = language_tool_python.utils.correct(line, matches)
        elif lang_lower == "en":
            line = correct_grammar(line)
            matches = tool_en.check(line)
            line = language_tool_python.utils.correct(line, matches)
        line = correct_punctuation(line, "kredor")
        line = clean_translation(line)
        result.append(line)
        if progress_callback:
            progress_callback(idx + 1, total)
    return result