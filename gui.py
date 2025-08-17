import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from subtitle_workflow import translate_subtitles

def run_gui():
    root = tk.Tk()
    root.title("Subtitle Translator")

    # Variables
    file_path = tk.StringVar()
    polish_only = tk.BooleanVar(value=False)
    LANG_OPTIONS = ["pl", "en"]
    FILE_TYPES = ["ass", "srt", "txt"]
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")
    file_type = tk.StringVar(value="ass")

    # Layout
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

    progress = ttk.Progressbar(
        root,
        orient="horizontal",
        length=300,
        mode="determinate",
        maximum=100
    )
    progress.grid(row=5, column=0, columnspan=3, pady=5)

    translation_stage_label = tk.Label(root, text="Translation: waiting")
    translation_stage_label.grid(row=6, column=0, columnspan=3)

    post_stage_label = tk.Label(root, text="Post-processing: waiting")
    post_stage_label.grid(row=7, column=0, columnspan=3)

    status_label = tk.Label(root, text="0%")
    status_label.grid(row=9, column=0, columnspan=3)

    # ——— UI Update Helpers ——————————————————————————————————————————

    def _apply_translate_ui(overall, phase_pct, overall_pct):
        translation_stage_label.config(text=f"Translation: {phase_pct}%")
        progress.config(value=overall)
        status_label.config(text=f"{overall_pct}%")
        root.update_idletasks()

    def _apply_post_ui(overall, phase_pct, overall_pct):
        post_stage_label.config(text=f"Post-processing: {phase_pct}%")
        progress.config(value=overall)
        status_label.config(text=f"{overall_pct}%")
        root.update_idletasks()

    # ——— Callbacks (run in worker thread) ——————————————————————————————

    def update_translation_progress(current, total):
        # DEBUG: verify this prints during translation
        print(f"[DBG] translate called: {current}/{total}")
        if total <= 0:
            return

        # translation occupies the first 50% of the bar
        overall = (current / total) * 50
        phase_pct = int((current / total) * 100)
        overall_pct = int(overall)

        # marshal UI update onto main thread
        root.after(0, _apply_translate_ui, overall, phase_pct, overall_pct)

    def update_post_progress(current, total):
        # DEBUG: verify this prints during post-processing
        print(f"[DBG] post called: {current}/{total}")
        if total <= 0:
            return

        # post-processing occupies the last 50% of the bar
        overall = 50 + (current / total) * 50
        phase_pct = int(((overall - 50) / 50) * 100)
        overall_pct = int(overall)

        # marshal UI update onto main thread
        root.after(0, _apply_post_ui, overall, phase_pct, overall_pct)

    # ——— File Browser & UI Reset —————————————————————————————————————

    def browse_file():
        ext = file_type.get()
        chosen = filedialog.askopenfilename(
            filetypes=[(f"{ext.upper()} Subtitle", f"*.{ext}")]
        )
        if chosen:
            file_path.set(chosen)

    def reset_ui():
        start_btn.config(state="normal")
        progress.config(value=0, mode="determinate")
        translation_stage_label.config(text="Translation: waiting")
        post_stage_label.config(text="Post-processing: waiting")
        status_label.config(text="0%")

    # ——— Main Translation Flow ————————————————————————————————————————

    def start_translation():
        path = file_path.get()
        if not (path and src_lang.get() and tgt_lang.get()):
            messagebox.showerror("Error", "Please fill all fields.")
            return

        try:
            output_path, _, _ = translate_subtitles(
                path,
                src_lang.get(),
                tgt_lang.get(),
                polish_only.get(),
                translation_callback=update_translation_progress,
                post_callback=update_post_progress
            )
            on_translation_success(output_path)
        except Exception as e:
            on_translation_error(e)

    def run_and_reset():
        try:
            start_translation()
        finally:
            # ensure UI always resets (even on exception)
            root.after(0, reset_ui)

    def start_translation_thread():
        start_btn.config(state="disabled")
        status_label.config(text="Starting translation…")
        threading.Thread(target=run_and_reset, daemon=True).start()

    def on_translation_success(output_path):
        progress.config(value=100)
        status_label.config(text="100%")
        messagebox.showinfo("Success", f"Translated file saved to:\n{output_path}")

    def on_translation_error(err):
        progress.config(value=0)
        status_label.config(text="Error")
        messagebox.showerror("Translation Failed", str(err))

    # ——— Start Button & Mainloop ——————————————————————————————————————

    start_btn = tk.Button(root, text="Start Translation", command=start_translation_thread)
    start_btn.grid(row=8, column=0, columnspan=3, pady=5)

    root.mainloop()

if __name__ == "__main__":
    run_gui()