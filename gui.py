# gui.py
import tkinter as tk
from tkinter import filedialog, messagebox
from subtitle_workflow import translate_subtitles

def run_gui():
    def browse_file():
        file_path.set(filedialog.askopenfilename(filetypes=[("ASS Subtitle", "*.ass")]))

    def start_translation():
        path = file_path.get()
        src = src_lang.get()
        tgt = tgt_lang.get()
        if not path or not src or not tgt:
            messagebox.showerror("Error", "Please fill all fields.")
            return
        try:
            output = translate_subtitles(path, src, tgt, polish_only.get())
            messagebox.showinfo("Success", f"Translated file saved to:\n{output}")
        except Exception as e:
            messagebox.showerror("Translation Failed", str(e))

    root = tk.Tk()
    root.title("ASS Subtitle Translator")

    file_path = tk.StringVar()
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")
    polish_only = tk.BooleanVar(value=False)

    tk.Label(root, text="Subtitle File (.ass):").grid(row=0, column=0, sticky="w")
    tk.Entry(root, textvariable=file_path, width=40).grid(row=0, column=1)
    tk.Button(root, text="Browse", command=browse_file).grid(row=0, column=2)

    tk.Label(root, text="Source Language Code:").grid(row=1, column=0, sticky="w")
    tk.Entry(root, textvariable=src_lang, width=10).grid(row=1, column=1)

    tk.Label(root, text="Target Language Code:").grid(row=2, column=0, sticky="w")
    tk.Entry(root, textvariable=tgt_lang, width=10).grid(row=2, column=1)

    tk.Label(root, text="Polish Only:").grid(row=3, column=0, sticky="w")
    tk.Checkbutton(root, variable=polish_only).grid(row=3, column=1, sticky="w")

    tk.Button(root, text="Start Translation", command=start_translation).grid(row=5, column=0, columnspan=3)

    root.mainloop()
