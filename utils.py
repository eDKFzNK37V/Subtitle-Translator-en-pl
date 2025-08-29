# utils.py
import pysubs2
import threading
import tkinter as tk
from tkinter import filedialog
import tkinter as tk
from tkinter import messagebox
def _detect_encoding(path, default="utf-8"):
    try:
        import chardet
        with open(path, "rb") as f:
            raw = f.read(4096)
        enc = chardet.detect(raw)["encoding"] or default
        return enc
    except Exception:
        return default

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
        enc = _detect_encoding(file_path)
        subs = pysubs2.load(file_path, encoding=enc)
        # Only return non-empty subtitle texts (skip empty, sequence numbers, etc.)
        texts = [event.text for event in subs if event.text.strip()]
        return texts, subs
    elif ext == "txt":
        enc = _detect_encoding(file_path)
        with open(file_path, encoding=enc, errors="replace") as f:
            lines = f.readlines()
        # Skip lines that are empty or look like sequence numbers (just digits)
        filtered = [line for line in lines if line.strip() and not line.strip().isdigit()]
        return filtered, None
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

def save_subtitle_lines(lines, file_path, subs=None):
    ext = file_path.split('.')[-1].lower()
    if ext in ["ass", "srt"] and subs:
        for i, line in enumerate(lines):
            #print(f"SAVING LINE {i}: {repr(line)}")  # Debug print
            subs[i].text = line.strip()
        subs.save(file_path, encoding="utf-8-sig", format=ext)  # <-- use utf-8-sig
    elif ext == "txt":
        with open(file_path, "w", encoding="utf-8-sig") as f:
            for line in lines:
                f.write(line.strip() + "\n")
    else:
        raise ValueError(f"Unsupported file format: .{ext}")
    

class PostProcessingController:
    def __init__(self):
        self.lock = threading.Lock()
        self.started = False

    def try_start(self):
        with self.lock:
            if self.started:
                print("[DBG] Skipping duplicate post-processing call")
                return False
            self.started = True
            return True

    def reset(self):
        with self.lock:
            self.started = False



def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"

def browse_file(var, ext):
    chosen = filedialog.askopenfilename(
        filetypes=[(f"{ext.upper()} Subtitle", f"*.{ext}")]
    )
    if chosen:
        var.set(chosen)
    return chosen

def update_formatting_widgets(file_type, formatting_cb, preview_btn):
    if file_type.get() == "txt":
        formatting_cb.grid()
        preview_btn.grid()
    else:
        formatting_cb.grid_remove()
        preview_btn.grid_remove()



# def show_txt_preview(parent, txt_path):
#     win = tk.Toplevel(parent); win.title("Preview & Options")
#     # … read + display file …
#     return win

# def review_txt_translations(parent, original_lines, translated_lines, on_save):
#     win = tk.Toplevel(parent); win.title("Review TXT")
#     # … build widgets …
#     save_btn = tk.Button(win, text="Save", command=lambda: on_save(...))
#     save_btn.pack()

# def review_translations(parent, originals, translations, on_save):
#     win = tk.Toplevel(parent); win.title("Review Subs")
#     # … build widgets …
#     save_btn = tk.Button(win, text="Save", command=lambda: on_save(...))
#     save_btn.pack()