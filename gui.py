# problem_gui.py

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from logs import SubtitleLogger
from utils import load_subtitle_lines, save_subtitle_lines
from subtitle_workflow import translate_subtitles
from pipeline import correct_text_batch
from progress_controller import ProgressController


def run_gui():
    root = tk.Tk()
    root.title("Subtitle Translator")

    # ─── Variables ───────────────────────────────────────────────────────────────
    file_path = tk.StringVar()
    polish_only = tk.BooleanVar(value=False)
    preserve_formatting = tk.BooleanVar(value=True)
    LANG_OPTIONS = ["pl", "en", "ja", "fr", "de"]
    FILE_TYPES = ["ass", "srt", "txt"]
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")
    file_type = tk.StringVar(value="ass")  # Default to .ass on startup

    # ─── Layout ──────────────────────────────────────────────────────────────────
    tk.Label(root, text="Subtitle File:").grid(row=0, column=0, sticky="w")
    tk.Entry(root, textvariable=file_path, width=40).grid(row=0, column=1, padx=5)
    tk.Button(root, text="Browse", command=lambda: browse_file()).grid(row=0, column=2)

    tk.Label(root, text="Source Language:").grid(row=1, column=0, sticky="w")
    tk.OptionMenu(root, src_lang, *LANG_OPTIONS).grid(row=1, column=1, sticky="w")

    tk.Label(root, text="Target Language:").grid(row=2, column=0, sticky="w")
    tk.OptionMenu(root, tgt_lang, *LANG_OPTIONS).grid(row=2, column=1, sticky="w")

    tk.Label(root, text="File Type:").grid(row=3, column=0, sticky="w")
    tk.OptionMenu(root, file_type, *FILE_TYPES).grid(row=3, column=1, sticky="w")

    tk.Checkbutton(root, text="Polish Only", variable=polish_only).grid(row=4, column=1, sticky="w")

    formatting_cb = tk.Checkbutton(
        root,
        text="Preserve formatting for .txt",
        variable=preserve_formatting
    )
    preview_btn = tk.Button(
        root,
        text="Preview Formatting",
        command=lambda: show_txt_preserve_formatting_popup(file_path.get())
    )
    formatting_cb.grid(row=5, column=0, sticky="w")
    preview_btn.grid(row=5, column=1, sticky="w")
    
    def update_formatting_widgets(*args):
        if file_type.get() == "txt":
            formatting_cb.grid()
            preview_btn.grid()
        else:
            formatting_cb.grid_remove()
            preview_btn.grid_remove()

    file_type.trace_add("write", update_formatting_widgets)
    update_formatting_widgets()

    # ─── Progress & Status ────────────────────────────────────────────────────────
    progress_var = tk.DoubleVar(value=0)
    ttk.Progressbar(
        root,
        orient="horizontal",
        length=400,
        mode="determinate",
        maximum=100,
        variable=progress_var
    ).grid(row=6, column=0, columnspan=3, pady=10)

    status_label      = tk.Label(root, text="0%")
    status_label.grid(row=7, column=0, columnspan=3)

    translation_label = tk.Label(root, text="Translation: waiting")
    translation_label.grid(row=8, column=0, columnspan=3)

    post_label        = tk.Label(root, text="Post-processing: waiting")
    post_label.grid(row=9, column=0, columnspan=3)

    # instantiate the controller
    controller = ProgressController(
        root,
        progress_var,
        translation_label,
        post_label,
        status_label
    )

    # ─── File Browse & Formatting Preview ────────────────────────────────────────
    def browse_file():
        ext = file_type.get()
        chosen = filedialog.askopenfilename(
            filetypes=[(f"{ext.upper()} Subtitle", f"*.{ext}")]
        )
        if chosen:
            file_path.set(chosen)

    def show_txt_preserve_formatting_popup(txt_path):
        if not txt_path:
            messagebox.showinfo("Info", "Please select a .txt file first.")
            return
        preview = tk.Toplevel(root)
        preview.title("TXT Formatting Preview")
        preview.geometry("800x600")
        with open(txt_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        text = tk.Text(preview, wrap="word", font=("Courier", 10))
        text.insert("1.0", content)
        text.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            preview,
            text="Formatting preserved. Only non-empty, non-numeric lines will be translated.",
            fg="blue"
        ).pack(pady=5)
        tk.Button(preview, text="OK", command=preview.destroy).pack(pady=10)

    # ─── Review Dialogs ─────────────────────────────────────────────────────────
    def review_txt_translations(orig, trans, out_path):
        review = tk.Toplevel(root); review.title("Review TXT Translation")
        review.geometry("900x600")
        review.protocol("WM_DELETE_WINDOW", lambda: (review.destroy(), on_translation_error("Canceled")))
        frame = tk.Frame(review); frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas)
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0,0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entries = []
        for idx, (o, t) in enumerate(zip(orig, trans)):
            if o.strip() and not o.strip().isdigit():
                tk.Label(scrollable, text=f"Line {idx+1}:", width=8, anchor="w")\
                  .grid(row=idx, column=0, sticky="w")
                tk.Label(
                    scrollable,
                    text=o.rstrip(),
                    width=40,
                    anchor="w",
                    wraplength=350,
                    fg="gray"
                ).grid(row=idx, column=1, sticky="w")
                ent = tk.Entry(scrollable, width=140)
                ent.insert(0, t.strip())
                ent.grid(row=idx, column=2, sticky="w")
                entries.append((idx, ent, o))
            else:
                tk.Label(
                    scrollable,
                    text=o.rstrip(),
                    width=120,
                    anchor="w"
                ).grid(row=idx, column=0, columnspan=3, sticky="w")

        def approve_and_save():
            lines = list(orig)
            for i, e, o in entries:
                lead  = len(o) - len(o.lstrip(" "))
                trail = len(o) - len(o.rstrip(" "))
                nl    = "\n" if o.endswith("\n") else ""
                lines[i] = " "*lead + e.get() + " "*trail + nl
            with open(out_path, "w", encoding="utf-8-sig") as out:
                out.writelines(lines)
            review.destroy()
            on_translation_success(out_path)

        tk.Button(review, text="Approve and Save", command=approve_and_save)\
          .pack(pady=10)

    def review_sub_translations(orig, trans, out_path):
        review = tk.Toplevel(root); review.title("Review Translations")
        review.geometry("900x600")
        review.protocol("WM_DELETE_WINDOW", lambda: (review.destroy(), on_translation_error("Canceled")))
        frame = tk.Frame(review); frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas)
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0,0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entries = []
        for i, (o, t) in enumerate(zip(orig, trans)):
            tk.Label(scrollable, text=f"Line {i+1}:", width=8, anchor="w")\
              .grid(row=i, column=0, sticky="w")
            tk.Label(
                scrollable,
                text=o.strip(),
                width=40,
                anchor="w",
                wraplength=350,
                fg="gray"
            ).grid(row=i, column=1, sticky="w")
            ent = tk.Entry(scrollable, width=120)
            ent.insert(0, t.strip())
            ent.grid(row=i, column=2, sticky="w")
            entries.append(ent)

        def approve_and_save():
            edited = [e.get() for e in entries]
            _, subs = load_subtitle_lines(file_path.get())
            save_subtitle_lines(edited, out_path, subs)
            review.destroy()
            on_translation_success(out_path)

        tk.Button(review, text="Approve and Save", command=approve_and_save)\
          .pack(pady=10)

    # ─── Main Translation Flow ──────────────────────────────────────────────────
    def start_translation():
        path = file_path.get()
        if not (path and src_lang.get() and tgt_lang.get()):
            messagebox.showerror("Error", "Please fill all fields.")
            return

        # Calculate number of translatable lines
        if file_type.get() == "txt" and preserve_formatting.get():
            with open(path, encoding="utf-8", errors="replace") as f:
                total_lines = sum(1 for line in f if line.strip() and not line.strip().isdigit())
        else:
            _, subs = load_subtitle_lines(path)
            total_lines = len(subs) if subs else 0

        controller.start(total_lines)

        # Translation phase
        try:
            output_path, originals, translated = translate_subtitles(
                path,
                src_lang.get(),
                tgt_lang.get(),
                polish_only.get(),
                translation_callback=controller.update_translation_progress
            )
        except Exception as e:
            on_translation_error(e)
            return

        # Switch UI to post-processing phase
        root.after(0, controller.show_post_start)

        # Post-processing in background (robust, per-line, non-blocking)
        def do_post():
            try:
                logger = SubtitleLogger(file_path.get(), tgt_lang.get())
                corrected = []
                total = len(translated)

                # Safety: if totals disagree, prefer the controller's total_lines
                post_total = total_lines if total_lines else total

                for idx, line in enumerate(translated):
                    try:
                        # Correct one line to keep UI responsive
                        corrected_line = correct_text_batch([line], tgt_lang.get())[0]
                    except Exception as line_err:
                        # Don’t freeze the whole job — fall back and keep going
                        corrected_line = line
                        print(f"[do_post] Correction failed on line {idx+1}: {line_err}")

                    # Log the outcome (even if we fell back)
                    try:
                        logger.log_entry(
                            idx,
                            originals[idx],
                            translated[idx],
                            corrected_line,
                            tags_before=[],
                            tags_after=[]
                        )
                    except Exception as log_err:
                        # Logging must never break the flow
                        print(f"[do_post] Logging failed on line {idx+1}: {log_err}")

                    corrected.append(corrected_line)

                    # One progress tick per line with the same total the controller expects
                    try:
                        controller.update_post_progress(idx + 1, post_total)
                    except Exception as prog_err:
                        print(f"[do_post] Progress update failed on line {idx+1}: {prog_err}")

                # Finalize logs (even if some lines failed)
                try:
                    logger.write_summary()
                except Exception as summ_err:
                    print(f"[do_post] Writing summary failed: {summ_err}")

                # Always open the review window on the main thread
                root.after(
                    0,
                    review_txt_translations if file_type.get() == "txt" and preserve_formatting.get()
                    else review_sub_translations,
                    originals, corrected, output_path
                )

            except Exception as e:
                # Any unexpected error in the post thread: surface it and reset UI
                on_translation_error(e)

        threading.Thread(target=do_post, daemon=True).start()
    def run_and_reset():
        try:
            start_translation()
        finally:
            # reset happens on success/error only
            pass

    def start_translation_thread():
        # validate first
        if not (file_path.get() and src_lang.get() and tgt_lang.get()):
            messagebox.showerror("Error", "Please fill all fields.")
            return
        start_btn.config(state="disabled")
        status_label.config(text="Starting translation…")
        threading.Thread(target=run_and_reset, daemon=True).start()

    # ─── Completion & Error Handlers ────────────────────────────────────────────
    def on_translation_success(out_path):
        start_btn.config(state="normal")
        controller.reset()
        messagebox.showinfo("Success", f"Translated file saved to:\n{out_path}")

    def on_translation_error(err):
        start_btn.config(state="normal")
        status_label.config(text="Error")
        messagebox.showerror("Translation Failed", str(err))
        controller.reset()

    # ─── Start Button ──────────────────────────────────────────────────────────
    start_btn = tk.Button(root, text="Start Translation", command=start_translation_thread)
    start_btn.grid(row=10, column=0, columnspan=3, pady=10)

    root.mainloop()


if __name__ == "__main__":
    run_gui()