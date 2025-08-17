import os
import json
import difflib
from datetime import datetime

POLISH_DIACRITICS = set("ąćęłńóśźż")

class SubtitleLogger:
    def __init__(self, file_path: str, lang: str):
        base = os.path.splitext(os.path.basename(file_path))[0]
        self.log_txt = os.path.join(os.path.dirname(file_path), f"{base}_log_{lang}.txt")
        self.log_json = os.path.join(os.path.dirname(file_path), f"{base}_log_{lang}.json")
        self.total_changes = 0
        self.entries = []

        # Clear previous logs
        for path in [self.log_txt, self.log_json]:
            if os.path.exists(path):
                os.remove(path)

        self._write_header()

    def _write_header(self):
        with open(self.log_txt, "w", encoding="utf-8") as f:
            f.write(f"Subtitle Change Log\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

    def _word_diff(self, original: str, corrected: str) -> str:
        orig_words = original.split()
        corr_words = corrected.split()
        diff = difflib.ndiff(orig_words, corr_words)
        return ' '.join([
            f"[{word[2:]}]" if word.startswith('+ ') or word.startswith('- ') else word[2:]
            for word in diff
        ])

    def _diacritics_added(self, before: str, after: str) -> list:
        return [char for char in after if char in POLISH_DIACRITICS and char not in before]

    def log_entry(self, index: int, original: str, translated: str, corrected: str, tags_before: list, tags_after: list):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.total_changes += 1

        word_diff = self._word_diff(translated, corrected)
        diacritics = self._diacritics_added(translated, corrected)

        entry = {
            "line": index + 1,
            "timestamp": timestamp,
            "original": original,
            "translated": translated,
            "corrected": corrected,
            "word_diff": word_diff,
            "diacritics_added": diacritics,
            "tags_before": tags_before,
            "tags_after": tags_after
        }
        self.entries.append(entry)

        # Print to console for comparison
        print(f"[Line {index + 1}] — {timestamp}")
        print(f"Original:   {original}")
        print(f"Translated: {translated}")
        print(f"Corrected:  {corrected}")
        print(f"Word Diff:  {word_diff}")
        if diacritics:
            print(f"Diacritics Added: {', '.join(diacritics)}")
        if tags_before != tags_after:
            print(f"Tags changed:")
            print(f"  Before: {tags_before}")
            print(f"  After:  {tags_after}")
        print("-" * 60)

        with open(self.log_txt, "a", encoding="utf-8") as f:
            f.write(f"[Line {index + 1}] — {timestamp}\n")
            f.write(f"Original:   {original}\n")
            f.write(f"Translated: {translated}\n")
            f.write(f"Corrected:  {corrected}\n")
            f.write(f"Word Diff:  {word_diff}\n")
            if diacritics:
                f.write(f"Diacritics Added: {', '.join(diacritics)}\n")
            if tags_before != tags_after:
                f.write(f"Tags changed:\n")
                f.write(f"  Before: {tags_before}\n")
                f.write(f"  After:  {tags_after}\n")
            f.write("-" * 60 + "\n")

    def write_summary(self):
        with open(self.log_txt, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"Summary:\n")
            f.write(f"Total lines changed: {self.total_changes}\n")
            f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n")

        with open(self.log_json, "w", encoding="utf-8") as f:
            json.dump({
                "generated": datetime.now().isoformat(),
                "total_changes": self.total_changes,
                "entries": self.entries
            }, f, indent=2, ensure_ascii=False)
