import language_tool_python
import os

# -----------------------------
# Polish diacritics dictionary
# -----------------------------
DIACRITIC_DICT = {}
try:
    dict_path = os.path.join("components", "polish_words_with_specials.txt")
    if os.path.exists(dict_path):
        with open(dict_path, encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    DIACRITIC_DICT[word.lower()] = word
    else:
        print(f"[Warning] DIACRITIC_DICT file not found: {dict_path}")
except Exception as e:
    print(f"[Error] Failed to load DIACRITIC_DICT: {e}")

# -----------------------------
# LanguageTool instances
# -----------------------------
tool_pl = None
tool_en = None

try:
    tool_pl = language_tool_python.LanguageTool('pl-PL')
except Exception as e:
    print(f"[Warning] Failed to initialize Polish LanguageTool: {e}")

try:
    tool_en = language_tool_python.LanguageTool('en-US')
except Exception as e:
    print(f"[Warning] Failed to initialize English LanguageTool: {e}")
