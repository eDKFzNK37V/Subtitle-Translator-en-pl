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
    print("[DBG] correct_text_batch called")

    total = len(lines)
    if progress_callback:
        progress_callback(0, total)

    if lang.lower() == "pl":
        print("[DBG] About to call tool_pl.check for all lines")
        matches = []
        for idx, line in enumerate(lines):
            print(f"[DBG] tool_pl.check line {idx+1}/{len(lines)}")
            matches.append(tool_pl.check(line))
            if progress_callback:
                progress_callback(idx + 1, total)
        print("[DBG] Finished tool_pl.check for all lines")
        lines = [language_tool_python.utils.correct(line, match)
                 for line, match in zip(lines, matches)]

    elif lang.lower() == "en":
        lines = [correct_grammar(line) for line in lines]
        matches = []
        for idx, line in enumerate(lines):
            matches.append(tool_en.check(line))
            if progress_callback:
                progress_callback(idx + 1, total)
        lines = [language_tool_python.utils.correct(line, match)
                 for line, match in zip(lines, matches)]

    result = []
    for i, line in enumerate(lines):
        line = correct_punctuation(line, "kredor")
        line = clean_translation(line)
        result.append(line)
        if progress_callback and ((i + 1) % 20 == 0 or (i + 1) == total):
            progress_callback(i + 1, total)

    return result
