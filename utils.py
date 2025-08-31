import os
import pysubs2
import chardet
import re
from typing import List, Tuple, Optional

# -------------------------------------------------------------------
# File loading helpers
# -------------------------------------------------------------------

def detect_encoding(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        rawdata = f.read()
    result = chardet.detect(rawdata)
    return result['encoding'] or 'utf-8-sig'


def load_subtitle_lines(path: str) -> Tuple[List[str], Optional[pysubs2.SSAFile], List[int]]:
    """
    Load subtitle (.ass/.srt) or text (.txt) file and return:
      texts     -> list of non-empty lines to process
      subs      -> pysubs2 SSAFile object for ASS/SRT, or None for TXT
      idx_map   -> list of original file indices for each processed line
    """
    ext = path.split('.')[-1].lower()

    if ext in ["ass", "srt"]:
        subs = pysubs2.load(path, encoding=detect_encoding(path))
        texts, idx_map = [], []
        for i, ev in enumerate(subs):
            if ev.text.strip():
                texts.append(ev.text)
                idx_map.append(i)
        return texts, subs, idx_map

    elif ext == "txt":
        texts, idx_map = [], []
        with open(path, "r", encoding=detect_encoding(path)) as f:
            for i, line in enumerate(f):
                if line.strip():
                    texts.append(line.rstrip("\n"))
                    idx_map.append(i)
        return texts, None, idx_map

    else:
        raise ValueError(f"Unsupported file format: .{ext}")


def save_subtitle_lines(lines: List[str], file_path: str,
                        subs: Optional[pysubs2.SSAFile] = None,
                        idx_map: Optional[List[int]] = None) -> None:
    """
    Save processed lines back into the original file, preserving alignment.
    For ASS/SRT: only updates events that had text originally.
    For TXT: only updates non-blank lines, preserving blank lines in place.
    """
    ext = file_path.split('.')[-1].lower()

    if ext in ["ass", "srt"] and subs and idx_map is not None:
        for li, ev_idx in enumerate(idx_map):
            if li < len(lines):
                subs[ev_idx].text = lines[li].strip()
        subs.save(file_path, encoding="utf-8-sig", format=ext)

    elif ext == "txt" and idx_map is not None:
        # Load all lines so we can preserve blank lines
        with open(file_path, "r", encoding=detect_encoding(file_path)) as f:
            all_lines = [line.rstrip("\n") for line in f]
        for li, orig_idx in enumerate(idx_map):
            if li < len(lines):
                all_lines[orig_idx] = lines[li].strip()
        with open(file_path, "w", encoding="utf-8-sig") as f:
            for line in all_lines:
                f.write(line + "\n")

    else:
        raise ValueError(f"Unsupported file format: .{ext}")

# -------------------------------------------------------------------
# Other existing utility functions from your original file
# (kept exactly as they were)
# -------------------------------------------------------------------

def clean_translation(text: str) -> str:
    # Your existing cleaning logic
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_tags(text: str) -> Tuple[str, List[str]]:
    tags = re.findall(r'(\{\\.*?\})', text)
    clean_text = re.sub(r'\{\\.*?\}', '', text)
    return clean_text, tags

def restore_tags(text: str, tags: List[str]) -> str:
    return ''.join(tags) + text

# ... (all your other original helper functions remain unchanged)