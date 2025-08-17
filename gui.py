import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from subtitle_workflow import translate_subtitles, create_comparison_subs
import threading

def run_gui():
    root = tk.Tk()
    root.title("Subtitle Translator")

    file_path = tk.StringVar()
    polish_only = tk.BooleanVar(value=False)
    LANG_OPTIONS = ["pl", "en"]
    FILE_TYPES = ["ass", "srt", "txt"]
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")
    file_type = tk.StringVar(value="ass")

    # --- GUI Layout ---
    tk.Label(root, text="Subtitle File:").grid(row=0, column=0, sticky="w")
    tk.Entry(root, textvariable=file_path, width=40).grid(row=0, column=1)
    tk.Button(root, text="Browse", command=lambda: browse_file()).grid(row=0, column=2)

    tk.Label(root, text="Source Language:").grid(row=1, column=0, sticky="w")
    tk.OptionMenu(root, src_lang, *LANG_OPTIONS).grid(row=1, column=1, sticky="w")
    tk.Label(root, text="Target Language:").grid(row=2, column=0, sticky="w")
    tk.OptionMenu(root, tgt_lang, *LANG_OPTIONS).grid(row=2, column=1, sticky="w")

    tk.Label(root, text="File Type:").grid(row=3, column=0, sticky="w")
    tk.OptionMenu(root, file_type, *FILE_TYPES).grid(row=3, column=1, sticky="w")

    tk.Label(root, text="Polish Only:").grid(row=4, column=0, sticky="w")
    tk.Checkbutton(root, variable=polish_only).grid(row=4, column=1, sticky="w")

    status_label = tk.Label(root, text="Ready")
    status_label.grid(row=7, column=0, columnspan=3)

    progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", maximum=100)
    progress.grid(row=5, column=0, columnspan=3, pady=5)

    start_btn = tk.Button(root, text="Start Translation", command=lambda: start_translation_thread())
    start_btn.grid(row=6, column=0, columnspan=3, pady=5)

    # --- Functions ---
    def browse_file():
        ext = file_type.get()
        filetypes = [(f"{ext.upper()} Subtitle", f"*.{ext}")]
        file_path.set(filedialog.askopenfilename(filetypes=filetypes))

    def start_translation_thread():
        start_btn.config(state="disabled")
        progress.config(mode="indeterminate")
        progress.start()
        status_label.config(text="Starting translation...")
        threading.Thread(target=run_and_enable, daemon=True).start()

    def reset_ui():
        start_btn.config(state="normal")
        progress["value"] = 0
        status_label.config(text="Done")

    def run_and_enable():
        try:
            start_translation()
        finally:
            root.after(0, reset_ui)

    def update_progress(current, total):
        percent = (current / total) * 100
        def set_value():
            if progress["mode"] != "determinate":
                progress.stop()
                progress.config(mode="determinate")
            progress["value"] = percent
            status_label.config(text=f"Translating... {int(percent)}%")
        root.after(0, set_value)

    def start_translation():
        path = file_path.get()
        src = src_lang.get()
        tgt = tgt_lang.get()
        ext = file_type.get()

        if not path or not src or not tgt:
            root.after(0, lambda: messagebox.showerror("Error", "Please fill all fields."))
            return

        try:
            output_path, originals, corrected = translate_subtitles(
                path, src, tgt, polish_only.get(), progress_callback=update_progress
            )
            root.after(0, lambda: on_translation_success(output_path, originals, corrected, ext))
        except Exception as e:
            root.after(0, lambda err=e: on_translation_error(err))

    def on_translation_success(output_path, originals, corrected, ext):
        messagebox.showinfo("Success", f"Translated file saved to:\n{output_path}")
        if messagebox.askyesno("Create Comparison?", "Generate comparison file?"):
            save_to = filedialog.asksaveasfilename(defaultextension=f".{ext}")
            if save_to:
                create_comparison_subs(originals, corrected, save_to)
                messagebox.showinfo("Done", f"Comparison saved to:\n{save_to}")

    def on_translation_error(err):
        messagebox.showerror("Translation Failed", str(err))

    progress["value"] = 0
    root.mainloop()