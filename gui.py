# gui.py
import tkinter as tk
from tkinter import filedialog, messagebox
from subtitle_workflow import translate_subtitles, create_comparison_subs

def run_gui():
    def browse_file():
        ext = file_type.get()
        filetypes = [(f"{ext.upper()} Subtitle", f"*.{ext}")]
        file_path.set(filedialog.askopenfilename(filetypes=filetypes))

    def start_translation():
        path = file_path.get()
        src = src_lang.get()
        tgt = tgt_lang.get()
        ext = file_type.get()
        if not path or not src or not tgt:
            messagebox.showerror("Error", "Please fill all fields.")
            return
        try:
            output_path, original_lines, corrected_lines = translate_subtitles(path, src, tgt, polish_only.get())
            messagebox.showinfo("Success", f"Translated file saved to:\n{output_path}")
            
            if messagebox.askyesno("Create Comparison?", "Do you want to generate a comparison subtitle file?"):
                comparison_path = filedialog.asksaveasfilename(defaultextension=f".{ext}")
                if comparison_path:
                    create_comparison_subs(original_lines, corrected_lines, comparison_path)
                    messagebox.showinfo("Comparison Created", f"Comparison file saved to:\n{comparison_path}")
        except Exception as e:
            messagebox.showerror("Translation Failed", str(e))

    # GUI setup
    root = tk.Tk()
    root.title("Subtitle Translator")

    file_path = tk.StringVar()
    polish_only = tk.BooleanVar(value=False)

    # Dropdown options
    LANG_OPTIONS = ["pl", "en", "de", "fr", "es", "it"]
    FILE_TYPES = ["ass", "srt", "txt"]

    src_lang = tk.StringVar(value="pl")
    tgt_lang = tk.StringVar(value="en")
    file_type = tk.StringVar(value="ass")

    # File selection
    tk.Label(root, text="Subtitle File:").grid(row=0, column=0, sticky="w")
    tk.Entry(root, textvariable=file_path, width=40).grid(row=0, column=1)
    tk.Button(root, text="Browse", command=browse_file).grid(row=0, column=2)

    # Language selection
    tk.Label(root, text="Source Language:").grid(row=1, column=0, sticky="w")
    tk.OptionMenu(root, src_lang, *LANG_OPTIONS).grid(row=1, column=1, sticky="w")

    tk.Label(root, text="Target Language:").grid(row=2, column=0, sticky="w")
    tk.OptionMenu(root, tgt_lang, *LANG_OPTIONS).grid(row=2, column=1, sticky="w")

    # File type selection
    tk.Label(root, text="File Type:").grid(row=3, column=0, sticky="w")
    tk.OptionMenu(root, file_type, *FILE_TYPES).grid(row=3, column=1, sticky="w")

    # Polish-only toggle
    tk.Label(root, text="Polish Only:").grid(row=4, column=0, sticky="w")
    tk.Checkbutton(root, variable=polish_only).grid(row=4, column=1, sticky="w")

    # Action button
    tk.Button(root, text="Start Translation", command=start_translation).grid(row=6, column=0, columnspan=3)

    root.mainloop()

