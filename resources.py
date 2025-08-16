import language_tool_python

DIACRITIC_DICT = {}
with open(r"components/polish_words_with_specials.txt", encoding="utf-8") as f:
    for line in f:
        word = line.strip()
        if word:
            DIACRITIC_DICT[word.lower()] = word

tool_pl = language_tool_python.LanguageTool('pl-PL')
tool_en = language_tool_python.LanguageTool('en-US')
