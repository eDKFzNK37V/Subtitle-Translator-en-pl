import language_tool_python
from text_tools import restore_diacritics, correct_punctuation, correct_grammar, clean_translation
from resources import tool_pl, tool_en
from utils import load_subtitle_lines


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

