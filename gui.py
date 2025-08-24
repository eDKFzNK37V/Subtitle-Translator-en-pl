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
    preserve_formatting = tk.BooleanVar(value=True)
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
    file_type_menu = tk.OptionMenu(root, file_type, *FILE_TYPES)
    file_type_menu.grid(row=3, column=1, sticky="w")

    # Formatting preservation checkbox and preview button (only for .txt)
    formatting_checkbox = tk.Checkbutton(root, text="Preserve formatting for .txt", variable=preserve_formatting)
    formatting_checkbox.grid(row=4, column=2, sticky="w")
    formatting_checkbox.grid_remove()

    def show_formatting_preview():
        if file_path.get():
            show_txt_preserve_formatting_popup(file_path.get())
        else:
            messagebox.showinfo("Info", "Please select a .txt file first.")

    preview_btn = tk.Button(root, text="Preview Formatting", command=show_formatting_preview)
    preview_btn.grid(row=4, column=3, sticky="w")
    preview_btn.grid_remove()

    def update_formatting_widgets(*args):
        if file_type.get() == "txt":
            formatting_checkbox.grid()
            preview_btn.grid()
        else:
            formatting_checkbox.grid_remove()
            preview_btn.grid_remove()

    file_type.trace_add('write', update_formatting_widgets)
    update_formatting_widgets()

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
    def show_txt_preserve_formatting_popup(txt_path):
        #Read the file and show a preview with option to preserve formatting
        preview_win = tk.Toplevel(root)
        preview_win.title("TXT Formatting Preview & Options")
        preview_win.geometry("800x600")

        with open(txt_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        text_widget = tk.Text(preview_win, wrap="word", font=("Courier", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert("1.0", "".join(lines))
        # text_widget.config(state="disabled")

        info = tk.Label(preview_win, text="Formatting will be preserved. Only non-empty, non-formatting lines will be translated.", fg="blue")
        info.pack(pady=5)

        def close_preview():
            preview_win.destroy()

        close_btn = tk.Button(preview_win, text="OK", command=close_preview)
        close_btn.pack(pady=10)

    def browse_file():
        ext = file_type.get()
        chosen = filedialog.askopenfilename(
            filetypes=[(f"{ext.upper()} Subtitle", f"*.{ext}")]
        )
        if chosen:
            file_path.set(chosen)
            # #if ext == "txt":
            #     show_txt_preserve_formatting_popup(chosen)



    # Update review_translations for .txt to preserve formatting
    def review_txt_translations(original_lines, translated_lines, output_path):
        # Show a popup with original and translated lines, preserving formatting
        review_win = tk.Toplevel(root)
        review_win.title("Review TXT Translation (Formatting Preserved)")
        review_win.geometry("900x600")

        frame = tk.Frame(review_win)
        frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entry_widgets = []
        for i, (orig, trans) in enumerate(zip(original_lines, translated_lines)):
            # Only allow editing for lines that were translated (non-formatting)
            if orig.strip() and not orig.strip().isdigit():
                tk.Label(scrollable_frame, text=f"Line {i+1}:", anchor="w", width=8).grid(row=i, column=0, sticky="w")
                tk.Label(scrollable_frame, text=orig.rstrip(), anchor="w", width=40, wraplength=350, fg="gray").grid(row=i, column=1, sticky="w")
                entry = tk.Entry(scrollable_frame, width=120)
                entry.insert(0, trans.strip())
                entry.grid(row=i, column=2, sticky="w")
                entry_widgets.append((i, entry, orig))
            else:
                # Show formatting/blank lines as non-editable
                tk.Label(scrollable_frame, text=orig.rstrip(), anchor="w", width=120, fg="black").grid(row=i, column=0, columnspan=3, sticky="w")

        def approve_and_save():
            # Reconstruct the file, replacing only translated lines
            new_lines = list(original_lines)
            for idx, entry, orig in entry_widgets:
                leading = len(orig) - len(orig.lstrip(' '))
                trailing = len(orig) - len(orig.rstrip(' '))
                has_newline = orig.endswith('\n')
                new_line = (' ' * leading) + entry.get() + (' ' * trailing) + ('\n' if has_newline else '')
                new_lines[idx] = new_line
            with open(output_path, "w", encoding="utf-8-sig") as f:
                f.writelines(new_lines)
            review_win.destroy()
            on_translation_success(output_path)
            root.after(0, reset_ui)

        approve_btn = tk.Button(review_win, text="Approve and Save", command=approve_and_save)
        approve_btn.pack(pady=10)

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
            def show_post_processing_start():
                post_stage_label.config(text="Post-processing: 0%")
                progress.config(value=50)
                status_label.config(text="50%")
                root.update_idletasks()

            if file_type.get() == "txt" and preserve_formatting.get():
                from utils import _detect_encoding
                enc = _detect_encoding(path)
                with open(path, encoding=enc, errors="replace") as f:
                    original_lines = f.readlines()
                to_translate = [line for line in original_lines if line.strip() and not line.strip().isdigit()]
                from subtitle_workflow import translate_subtitles
                # Translation stage
                _, _, translated_lines = translate_subtitles(
                    path,
                    src_lang.get(),
                    tgt_lang.get(),
                    polish_only.get(),
                    translation_callback=update_translation_progress,
                    post_callback=None
                )
                # Immediately show post-processing start
                root.after(0, show_post_processing_start)
                # Post-processing stage
                from pipeline import correct_text_batch
                corrected_lines = correct_text_batch(
                    translated_lines,
                    tgt_lang.get(),
                    progress_callback=update_post_progress
                )
                # Map translations back to original structure, preserving all whitespace
                translated_iter = iter(corrected_lines)
                mapped_translations = []
                for line in original_lines:
                    if line.strip() and not line.strip().isdigit():
                        try:
                            translated = next(translated_iter)
                        except StopIteration:
                            translated = line.rstrip('\n')
                        leading = len(line) - len(line.lstrip(' '))
                        trailing = len(line) - len(line.rstrip(' '))
                        has_newline = line.endswith('\n')
                        new_line = (' ' * leading) + translated + (' ' * trailing) + ('\n' if has_newline else '')
                        mapped_translations.append(new_line)
                    else:
                        mapped_translations.append(line)
                import os
                ext = path.split('.')[-1].lower()
                output_path = os.path.splitext(path)[0] + f"_{tgt_lang.get()}.{ext}"
                review_txt_translations(original_lines, mapped_translations, output_path)
            else:
                # Translation stage
                output_path, originals, translated_lines = translate_subtitles(
                    path,
                    src_lang.get(),
                    tgt_lang.get(),
                    polish_only.get(),
                    translation_callback=update_translation_progress,
                    post_callback=None
                )
                # Immediately show post-processing start
                root.after(0, show_post_processing_start)
                # Post-processing stage
                from pipeline import correct_text_batch
                corrected_lines = correct_text_batch(
                    translated_lines,
                    tgt_lang.get(),
                    progress_callback=update_post_progress
                )
                # Show review popup before saving
                review_translations(originals, corrected_lines, output_path)
        except Exception as e:
            on_translation_error(e)

    def review_translations(originals, translations, output_path):
        review_win = tk.Toplevel(root)
        review_win.title("Review Translations")
        review_win.geometry("900x600")

        frame = tk.Frame(review_win)
        frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entry_widgets = []
        for i, (orig, trans) in enumerate(zip(originals, translations)):
            tk.Label(scrollable_frame, text=f"Line {i+1}:", anchor="w", width=8).grid(row=i, column=0, sticky="w")
            tk.Label(scrollable_frame, text=orig.strip(), anchor="w", width=40, wraplength=350, fg="gray").grid(row=i, column=1, sticky="w")
            entry = tk.Entry(scrollable_frame, width=120)
            entry.insert(0, trans.strip())
            entry.grid(row=i, column=2, sticky="w")
            entry_widgets.append(entry)

        def approve_and_save():
            # Collect possibly edited translations
            edited = [e.get() for e in entry_widgets]
            # Save using utils.save_subtitle_lines
            from utils import save_subtitle_lines, load_subtitle_lines
            _, subs = load_subtitle_lines(file_path.get())
            save_subtitle_lines(edited, output_path, subs)
            review_win.destroy()
            on_translation_success(output_path)
            # Reset UI after review and save
            root.after(0, reset_ui)

        approve_btn = tk.Button(review_win, text="Approve and Save", command=approve_and_save)
        approve_btn.pack(pady=10)

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