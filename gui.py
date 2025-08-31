# problem_gui.py
import sys
import traceback
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os

from logs import SubtitleLogger
from utils import load_subtitle_lines, save_subtitle_lines
from pipeline import correct_text_batch, translate_with_context
from progress_controller import ProgressController
from text_tools import extract_tags_with_placeholders, restore_tags_from_placeholders

logging.basicConfig(filename="error.log", level=logging.ERROR)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    detailed_message = (
        f"\n[ERROR] {exc_type.__name__}: {exc_value}\n"
        f"Traceback:\n{tb_str}"
    )
    logging.error(detailed_message)
    messagebox.showerror(
        "Unexpected Error",
        f"{exc_type.__name__}: {exc_value}\n\n"
        "See error.log for full details."
    )


sys.excepthook = handle_exception


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

    status_label = tk.Label(root, text="0%")
    status_label.grid(row=7, column=0, columnspan=3)

    translation_label = tk.Label(root, text="Translation: waiting")
    translation_label.grid(row=8, column=0, columnspan=3)

    post_label = tk.Label(root, text="Post-processing: waiting")
    post_label.grid(row=9, column=0, columnspan=3)

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
    def review_txt_translations(orig_nonempty, trans, out_path, log_path):
        fresh_orig, _, _ = load_subtitle_lines(file_path.get())

        review = tk.Toplevel(root)
        review.title("Review TXT Translation")
        review.geometry("900x600")
        review.protocol("WM_DELETE_WINDOW", lambda: (review.destroy(), on_translation_error("Canceled")))
        frame = tk.Frame(review)
        frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas)
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entries = []
        count = min(len(fresh_orig), len(trans))
        for idx in range(count):
            o = fresh_orig[idx]
            t = trans[idx]
            tk.Label(scrollable, text=f"Line {idx+1}:", width=8, anchor="w").grid(row=idx, column=0, sticky="w")
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
            entries.append(ent)

        def approve_and_save():
            try:
                edited = [e.get() for e in entries]
                restored = [
                    restore_tags_from_placeholders(edited[i], placeholder_maps[i])
                    for i in range(len(edited))
                ]
                save_subtitle_lines(restored, out_path, None, idx_map)
                review.destroy()
                on_translation_success(out_path, log_path)
            except Exception as e:
                logging.exception("[review_txt] Save failed")
                on_translation_error(e)

        tk.Button(review, text="Approve and Save", command=approve_and_save).pack(pady=10)

    def review_sub_translations(orig_nonempty, trans, out_path, log_path):
        fresh_orig, _, _ = load_subtitle_lines(file_path.get())

        review = tk.Toplevel(root)
        review.title("Review Translations")
        review.geometry("900x600")
        review.protocol("WM_DELETE_WINDOW", lambda: (review.destroy(), on_translation_error("Canceled")))
        frame = tk.Frame(review)
        frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas)
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        entries = []
        count = min(len(fresh_orig), len(trans))
        for i in range(count):
            o = fresh_orig[i]
            t = trans[i]
            tk.Label(scrollable, text=f"Line {i+1}:", width=12, anchor="w").grid(row=i, column=0, sticky="w")
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
            try:
                edited = [e.get() for e in entries]
                restored = [
                    restore_tags_from_placeholders(edited[i], placeholder_maps[i])
                    for i in range(len(edited))
                ]
                save_subtitle_lines(restored, out_path, subs, idx_map)
                review.destroy()
                on_translation_success(out_path, log_path)
            except Exception as e:
                logging.exception("[review_subs] Save failed")
                on_translation_error(e)

        tk.Button(review, text="Approve and Save", command=approve_and_save).pack(pady=10)

    # ─── Main Translation Flow ──────────────────────────────────────────────────
    def start_translation():
        path = file_path.get()
        if not (path and src_lang.get() and tgt_lang.get()):
            messagebox.showerror("Error", "Please fill all fields.")
            return

        texts, subs_loaded, idx_map_loaded = load_subtitle_lines(path)
        if not texts:
            messagebox.showerror("Error", "No subtitle lines found.")
            return

        nonlocal subs, idx_map, originals, pristine_originals, output_path, translated, placeholder_maps
        subs = subs_loaded
        idx_map = idx_map_loaded
        originals = texts[:]
        pristine_originals = texts[:]

        placeholder_maps = [extract_tags_with_placeholders(line)[1] for line in texts]

        total_lines = len(texts)
        controller.start(total_lines)

        try:
            translated = translate_with_context(
                texts,
                src_lang.get(),
                tgt_lang.get(),
                polish_only.get(),
                translation_callback=controller.update_translation_progress
            )
            base, ext = os.path.splitext(path)
            tgt = tgt_lang.get()
            output_path = f"{base}_{tgt}{ext}"
            save_subtitle_lines(translated, output_path, subs, idx_map)
        except Exception as e:
            logging.exception("[translate] Failed")
            on_translation_error(e)
            return

        controller.set_post_total(len(translated))

        try:
            warmup_sentence = (
                "To jest testowe zdanie." if tgt_lang.get().lower() == "pl"
                else "This is a test sentence."
            )
            correct_text_batch([warmup_sentence], tgt_lang.get())
        except Exception as warm_err:
            logging.warning(f"[prewarm] Correction warm‑up failed: {warm_err}")

        root.after(0, controller.show_post_start)

        def do_post():
            try:
                logger = SubtitleLogger(file_path.get(), tgt_lang.get(), idx_map=idx_map)
                total = len(translated)
                corrected_all = []

                root.after(0, lambda: controller.update_post_progress(1, total))
                root.after(0, lambda: controller.post_label.config(text="Post-processing: starting…"))

                stop_flag = {"stop": False}
                def heartbeat():
                    if not stop_flag["stop"]:
                        controller.update_post_progress(controller.p_current, total)
                        root.after(500, heartbeat)
                root.after(0, heartbeat)

                warmup_size = min(1, total)
                if warmup_size:
                    try:
                        batch = translated[:warmup_size]
                        cb = correct_text_batch(
                            batch, tgt_lang.get(),
                            progress_callback=lambda done, _: controller.update_post_progress(done, total)
                        )
                        corrected_all.extend(cb or [])
                    except Exception as e:
                        logging.exception(f"[do_post] Warm-up batch failed: {e}")

                batch_size = 8
                for start in range(warmup_size, total, batch_size):
                    end = min(start + batch_size, total)
                    batch = translated[start:end]
                    try:
                        cb = correct_text_batch(
                            batch, tgt_lang.get(),
                            progress_callback=lambda done, _, offset=start: controller.update_post_progress(done + offset, total)
                        )
                        corrected_all.extend(cb or [])
                    except Exception as e:
                        logging.exception(f"[do_post] Error in batch {start}-{end}: {e}")
                        # Skip this batch but continue
                        corrected_all.extend(batch)  # keep alignment by falling back to untranslated batch

                if len(corrected_all) < total:
                    corrected_all.extend(translated[len(corrected_all):total])

                stop_flag["stop"] = True
                root.after(0, lambda: controller.update_post_progress(total, total))

                for idx, (orig, trans, corr) in enumerate(zip(originals, translated, corrected_all)):
                    try:
                        logger.log_entry(idx, orig, trans, corr, tags_before=[], tags_after=[])
                    except Exception:
                        logging.exception(f"[do_post] Logging failed on line {idx+1}")
                try:
                    logger.write_summary()
                except Exception:
                    logging.exception("[do_post] Failed writing summary")

                log_path = logger.get_log_path() if hasattr(logger, "get_log_path") else logger.log_txt
                review_fn = review_txt_translations if file_type.get() == "txt" else review_sub_translations
                root.after(0, review_fn, pristine_originals, corrected_all, output_path, log_path)

            except Exception as e:
                logging.exception(f"[do_post] Unhandled exception: {e}")
                on_translation_error(e)
        threading.Thread(target=do_post, daemon=True).start()

    subs = None
    idx_map = []
    originals = []
    pristine_originals = []
    translated = []
    output_path = ""
    placeholder_maps = []

    def run_and_reset():
        try:
            start_translation()
        finally:
            pass

    def start_translation_thread():
        if not (file_path.get() and src_lang.get() and tgt_lang.get()):
            messagebox.showerror("Error", "Please fill all fields.")
            return
        start_btn.config(state="disabled")
        status_label.config(text="Starting translation…")
        threading.Thread(target=run_and_reset, daemon=True).start()

    def on_translation_success(out_path: str, log_path: str | None = None):
        start_btn.config(state="normal")
        controller.reset()
        messagebox.showinfo("Success", f"Translated file saved to:\n{out_path}")
        if log_path:
            messagebox.showinfo("Success", f"Log file saved to:\n{log_path}")

    def on_translation_error(err):
        start_btn.config(state="normal")
        status_label.config(text="Error")
        messagebox.showerror("Translation Failed", str(err))
        controller.reset()

    start_btn = tk.Button(root, text="Start Translation", command=start_translation_thread)
    start_btn.grid(row=10, column=0, columnspan=3, pady=10)

    root.mainloop()


if __name__ == "__main__":
    run_gui()