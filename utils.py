# utils.py
import pysubs2

def format_ass(text, style='normal'):
    """Apply ASS subtitle styling to text."""
    if style == 'italic':
        return r"{\i1}" + text + r"{\i0}"
    elif style == 'bold':
        return r"{\b1}" + text + r"{\b0}"
    return text

def load_subtitle_lines(file_path):
    ext = file_path.split('.')[-1].lower()
    if ext in ["ass", "srt"]:
        subs = pysubs2.load(file_path, encoding="utf-8")
        return [event.text for event in subs], subs
    elif ext == "txt":
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
        return lines, None
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

def save_subtitle_lines(lines, file_path, subs=None):
    ext = file_path.split('.')[-1].lower()
    if ext in ["ass", "srt"] and subs:
        for i, line in enumerate(lines):
            subs[i].text = line.strip()
        subs.save(file_path, encoding="utf-8", format=ext)
    elif ext == "txt":
        with open(file_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line.strip() + "\n")
    else:
        raise ValueError(f"Unsupported file format: .{ext}")
