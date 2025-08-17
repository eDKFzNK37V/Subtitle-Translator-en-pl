import language_tool_python
from text_tools import restore_diacritics, correct_punctuation, correct_grammar, clean_translation
from resources import tool_pl, tool_en

def correct_text(text, lang):
    if lang.lower() == "pl":
        text = restore_diacritics(text)
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

    if lang.lower() == "pl":
        lines = [restore_diacritics(line) for line in lines]
        matches = [tool_pl.check(line) for line in lines]
        lines = [language_tool_python.utils.correct(line, match)
                 for line, match in zip(lines, matches)]

    elif lang.lower() == "en":
        lines = [correct_grammar(line) for line in lines]
        matches = [tool_en.check(line) for line in lines]
        lines = [language_tool_python.utils.correct(line, match)
                 for line, match in zip(lines, matches)]

    result = []
    for i, line in enumerate(lines):
        line = correct_punctuation(line, "kredor")
        line = clean_translation(line)
        result.append(line)
        if progress_callback:
            progress_callback(i + 1, total)

    return result
