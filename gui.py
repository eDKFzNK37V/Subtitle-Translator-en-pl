import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from subtitle_workflow import translate_subtitles
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

    # --- Add these under your progress bar creation ---
    progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate", maximum=100)
    progress.grid(row=5, column=0, columnspan=3, pady=5)

    # Stage labels
    translation_stage_label = tk.Label(root, text="Translation: waiting")
    translation_stage_label.grid(row=6, column=0, columnspan=3)

    post_stage_label = tk.Label(root, text="Post-processing: waiting")
    post_stage_label.grid(row=7, column=0, columnspan=3)

    # Shift your start_btn and status_label down accordingly
    start_btn = tk.Button(root, text="Start Translation", command=lambda: start_translation_thread())
    start_btn.grid(row=8, column=0, columnspan=3, pady=5)

    status_label = tk.Label(root, text="Ready")
    status_label.grid(row=9, column=0, columnspan=3)

    # --- Functions ---
    def browse_file():
        ext = file_type.get()
        filetypes = [(f"{ext.upper()} Subtitle", f"*.{ext}")]
        file_path.set(filedialog.askopenfilename(filetypes=filetypes))


    def reset_ui():
        start_btn.config(state="normal")
        progress["value"] = 0
        status_label.config(text="Done")

    def run_and_enable():
        try:
            start_translation()
        finally:
            root.after(0, reset_ui)
    def update_translation_progress(current, total):
        if total <= 0: return
        overall = (current / total) * 50
        root.after(0, lambda: (
            progress.__setitem__("value", overall),
            translation_stage_label.config(text=f"Translation: {int((overall/50)*100)}%")
        ))

    def update_post_progress(current, total):
        if total <= 0: return
        overall = 50 + (current / total) * 50
        root.after(0, lambda: (
            progress.__setitem__("value", overall),
            post_stage_label.config(text=f"Post-processing: {int((overall-50)/50*100)}%")
        ))
        
    last_percent = {"value": -1}  # keeps track of last progress % to avoid redundant updates
    
    def update_progress(current, total):
        if total <= 0:
            return  # avoid division by zero
        
        percent = int((current / total) * 100)

        # Only update if percent has actually increased
        if percent != last_percent["value"]:
            last_percent["value"] = percent
            root.after(0, lambda: (
                progress.config(mode="determinate"),
                progress.__setitem__("value", percent),
                status_label.config(text=f"Translating... {percent}%")
            ))

    def start_translation_thread():
        start_btn.config(state="disabled")
        progress.config(mode="indeterminate")
        progress.stop()
        progress.config(mode="determinate")
        progress["value"] = 0
        translation_stage_label.config(text="Translation: waiting")
        post_stage_label.config(text="Post-processing: waiting")
        progress.start()
        status_label.config(text="Starting translation...")
        threading.Thread(target=run_and_enable, daemon=True).start()
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
                path,
                src,
                tgt,
                polish_only.get(),
                translation_callback=update_translation_progress,
                post_callback=update_post_progress
)
            root.after(0, lambda: on_translation_success(output_path, originals, corrected, ext))
        except Exception as e:
            root.after(0, lambda err=e: on_translation_error(err))

    def on_translation_success(output_path, originals, corrected, ext):
        messagebox.showinfo("Success", f"Translated file saved to:\n{output_path}")


    def on_translation_error(err):
        messagebox.showerror("Translation Failed", str(err))

    progress["value"] = 0
    root.mainloop()