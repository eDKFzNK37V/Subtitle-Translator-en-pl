import os
from datetime import datetime

class SubtitleLogger:
    def __init__(self, file_path, target_lang, idx_map=None):
        self.file_path = file_path
        self.target_lang = target_lang
        self.idx_map = idx_map or []
        self.entries = []
        self.log_txt = self._make_log_path(file_path)

    def _make_log_path(self, file_path):
        base, _ = os.path.splitext(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base}_log_{timestamp}.txt"

    def log_entry(self, idx, original, translated, corrected, tags_before=None, tags_after=None):
        """
        Record a single translation/correction entry.
        idx: index in the processed list (not the original file index)
        """
        source_index = self.idx_map[idx] if idx < len(self.idx_map) else None
        self.entries.append({
            "source_index": source_index,
            "original": original,
            "translated": translated,
            "corrected": corrected,
            "tags_before": tags_before or [],
            "tags_after": tags_after or []
        })

    def write_summary(self):
        """
        Write all logged entries to the log file in a human-readable format.
        """
        with open(self.log_txt, "w", encoding="utf-8-sig") as f:
            f.write(f"Log for: {self.file_path}\n")
            f.write(f"Target language: {self.target_lang}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")

            for entry in self.entries:
                idx_str = (
                    f"[Source index: {entry['source_index']}]"
                    if entry["source_index"] is not None
                    else "[Source index: ?]"
                )
                f.write(f"{idx_str}\n")
                f.write(f"Original: {entry['original']}\n")
                f.write(f"Translated: {entry['translated']}\n")
                f.write(f"Corrected: {entry['corrected']}\n")
                if entry["tags_before"] or entry["tags_after"]:
                    f.write(f"Tags before: {entry['tags_before']}\n")
                    f.write(f"Tags after: {entry['tags_after']}\n")
                f.write("\n")

    def get_log_path(self):
        return self.log_txt