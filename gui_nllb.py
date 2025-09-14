import sys
import traceback
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
from logs import SubtitleLogger
from utils import load_subtitle_lines, save_subtitle_lines
from subtitle_workflow import correct_text_batch_nllb, translate_with_context_nllb
from progress_controller import ProgressController
from text_tools import extract_tags_with_placeholders, restore_tags_from_placeholders
from models import get_nllb_globals
model, tokenizer, device = get_nllb_globals()




def run_gui_nllb():
    import tkinter as tk
    root = tk.Tk()
    root.title("Subtitle Translator (NLLB)")

    
    # TODO: Implement NLLB-specific GUI logic here

    # ─── Variables ───────────────────────────────────────────────────────────────
    file_path = tk.StringVar()
    polish_only = tk.BooleanVar(value=False)
    preserve_formatting = tk.BooleanVar(value=True)
    LANG_OPTIONS = ["pl", "en", "ja", "fr", "de"]
    FILE_TYPES = ["ass", "srt", "txt"]
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")
    file_type = tk.StringVar(value="ass")  # Default to .ass on startup
    n_tag_wordidx = tk.IntVar(value=0)
    # ─── Layout ──────────────────────────────────────────────────────────────────
    tk.Label(root, text="Subtitle File:").grid(row=0, column=0, sticky="w")
    tk.Entry(root, textvariable=file_path, width=40).grid(row=0, column=1, padx=5)
    tk.Button(root, text="Browse", command=lambda: browse_file()).grid(row=0, column=2)

    tk.Label(root, text="Source Language:").grid(row=1, column=0, sticky="w")
    src_lang_menu = tk.OptionMenu(root, src_lang, *LANG_OPTIONS)
    src_lang_menu.grid(row=1, column=1, sticky="w")

    tk.Label(root, text="Target Language:").grid(row=2, column=0, sticky="w")
    tgt_lang_menu = tk.OptionMenu(root, tgt_lang, *LANG_OPTIONS)
    tgt_lang_menu.grid(row=2, column=1, sticky="w")

    tk.Label(root, text="File Type:").grid(row=3, column=0, sticky="w")
    file_type_menu = tk.OptionMenu(root, file_type, *FILE_TYPES)
    file_type_menu.grid(row=3, column=1, sticky="w")

    polish_only_cb = tk.Checkbutton(root, text="Polish Only", variable=polish_only)
    polish_only_cb.grid(row=4, column=1, sticky="w")

    tk.Label(root, text="\\N tag word index:").grid(row=5, column=0, sticky="w")
    n_tag_wordidx_spin = tk.Spinbox(root, from_=0, to=50, textvariable=n_tag_wordidx, width=5)
    n_tag_wordidx_spin.grid(row=5, column=1, sticky="w")

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
        # After user approves, show flexion/grammar error preview
        def show_flexion_preview(lines):
            import language_tool_python
            tool = language_tool_python.LanguageTool('pl-PL')
            preview = tk.Toplevel(root)
            preview.title("Podgląd błędów fleksyjnych/gramatycznych (LanguageTool)")
            preview.geometry("900x600")
            text = tk.Text(preview, wrap="word", font=("Courier", 10))
            text.pack(fill=tk.BOTH, expand=True)
            for idx, line in enumerate(lines):
                matches = tool.check(line)
                if matches:
                    text.insert(tk.END, f"Linia {idx+1}: {line}\n", "err")
                    for m in matches:
                        text.insert(tk.END, f"  - {m.ruleId}: {m.message}\n", "msg")
                else:
                    text.insert(tk.END, f"Linia {idx+1}: {line}\n", "ok")
            text.tag_config("err", foreground="red")
            text.tag_config("msg", foreground="orange")
            text.tag_config("ok", foreground="black")
            tk.Button(preview, text="Zamknij", command=preview.destroy).pack(pady=10)
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
        # After user approves, show flexion/grammar error preview
        def show_flexion_preview(lines):
            import language_tool_python
            tool = language_tool_python.LanguageTool('pl-PL')
            preview = tk.Toplevel(root)
            preview.title("Podgląd błędów fleksyjnych/gramatycznych (LanguageTool)")
            preview.geometry("900x600")
            text = tk.Text(preview, wrap="word", font=("Courier", 10))
            text.pack(fill=tk.BOTH, expand=True)
            for idx, line in enumerate(lines):
                matches = tool.check(line)
                if matches:
                    text.insert(tk.END, f"Linia {idx+1}: {line}\n", "err")
                    for m in matches:
                        text.insert(tk.END, f"  - {m.ruleId}: {m.message}\n", "msg")
                else:
                    text.insert(tk.END, f"Linia {idx+1}: {line}\n", "ok")
            text.tag_config("err", foreground="red")
            text.tag_config("msg", foreground="orange")
            text.tag_config("ok", foreground="black")
            tk.Button(preview, text="Zamknij", command=preview.destroy).pack(pady=10)
        fresh_orig, _, _ = load_subtitle_lines(file_path.get())

        review = tk.Toplevel(root)
        review.title("Review Translations")
        review.geometry("900x600")
        review.protocol("WM_DELETE_WINDOW", lambda: (review.destroy(), on_translation_error("Canceled")))
        # Use a single canvas with a frame containing a 2-column grid for originals and translations
        frame = tk.Frame(review)
        frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        scrollable = tk.Frame(canvas)
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Add headers
        tk.Label(scrollable, text="Original", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=2)
        tk.Label(scrollable, text="Translation", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=2)

        entries = []
        count = min(len(fresh_orig), len(trans))
        for i in range(count):
            o = fresh_orig[i]
            t = trans[i]
            tk.Label(scrollable, text=f"{i+1}", width=4, anchor="e").grid(row=i+1, column=0, sticky="e")
            tk.Label(
                scrollable,
                text=o.strip(),
                width=50,
                anchor="w",
                wraplength=350,
                fg="gray"
            ).grid(row=i+1, column=1, sticky="w")
            ent = tk.Entry(scrollable, width=120)
            ent.insert(0, t.strip())
            ent.grid(row=i+1, column=2, sticky="w")
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
        # Ensure the correct engine is set for the pipeline
        import config
        config.selected_engine = "nllb"

        path = file_path.get()

        # Defensive check: Only allow 'en'/'pl' (or allowed LANG_OPTIONS) from GUI
        allowed_langs = ["en", "pl", "ja", "fr", "de"]
        if src_lang.get() not in allowed_langs or tgt_lang.get() not in allowed_langs:
            logging.warning(f"[GUI] Invalid language code from GUI: src={src_lang.get()}, tgt={tgt_lang.get()}")
            messagebox.showerror("Error", f"Invalid language code selected: {src_lang.get()} → {tgt_lang.get()}. Please use the dropdown.")
            return
        if not (path and src_lang.get() and tgt_lang.get()):
            messagebox.showerror("Error", "Please fill all fields.")
            return

        nonlocal subs, idx_map, originals, pristine_originals, output_path, translated, placeholder_maps
        path = file_path.get()

        # Defensive check: Only allow 'en'/'pl' (or allowed LANG_OPTIONS) from GUI
        allowed_langs = ["en", "pl", "ja", "fr", "de"]
        if src_lang.get() not in allowed_langs or tgt_lang.get() not in allowed_langs:
            logging.warning(f"[GUI] Invalid language code from GUI: src={src_lang.get()}, tgt={tgt_lang.get()}")
            messagebox.showerror("Error", f"Invalid language code selected: {src_lang.get()} → {tgt_lang.get()}. Please use the dropdown.")
            return
        if not (path and src_lang.get() and tgt_lang.get()):
            messagebox.showerror("Error", "Please fill all fields.")
            return

        texts, subs_loaded, idx_map_loaded = load_subtitle_lines(path)
        if not texts:
            messagebox.showerror("Error", "No subtitle lines found.")
            return

        # --- Remove \N tags and group dialogue lines before translation ---
        from text_tools import extract_newline_tags, insert_newline_tags_at_wordidx, group_dialogue_lines, split_grouped_translations
        n_wordidx = n_tag_wordidx.get()
        cleaned_lines = []
        n_tag_counts = []
        for line in texts:
            cleaned, n_count = extract_newline_tags(line)
            cleaned_lines.append(cleaned)
            n_tag_counts.append(n_count)
        # Group lines for translation
        grouped_lines, group_map = group_dialogue_lines(cleaned_lines)

        nonlocal subs, idx_map, originals, pristine_originals, output_path, translated, placeholder_maps
        subs = subs_loaded
        idx_map = idx_map_loaded
        originals = cleaned_lines[:]
        pristine_originals = cleaned_lines[:]

        # Now do placeholder/tag logic on cleaned_lines
        placeholder_maps = [extract_tags_with_placeholders(line)[1] for line in cleaned_lines]

        total_lines = len(grouped_lines)  # Use grouped lines for translation progress
        controller.start(total_lines)

        try:
            # Translate grouped lines
            translated_groups = translate_with_context_nllb(
                grouped_lines,
                src_lang.get(),
                tgt_lang.get(),
                model,
                tokenizer,
                device,
                polish_only.get(),
                translation_callback=controller.update_translation_progress
            )
            # Split translations back to original lines
            translated = split_grouped_translations(translated_groups, group_map)
            # Do NOT re-insert \N tags here; defer to post-processing
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
            correct_text_batch_nllb([warmup_sentence], src_lang.get(), tgt_lang.get())
        except Exception as warm_err:
            logging.warning(f"[prewarm] Correction warm‑up failed: {warm_err}")

        root.after(0, controller.show_post_start)

        def do_post():
            try:
                logger = SubtitleLogger(file_path.get(), tgt_lang.get(), idx_map=idx_map)
                total = len(translated)
                corrected_all = []
                root.after(0, lambda: controller.post_label.config(text="Post-processing: starting…"))

                stop_flag = {"stop": False}
                def heartbeat():
                    if not stop_flag["stop"]:
                        controller.update_post_progress(controller.p_current, total)
                        # Force UI update even when window is not in focus
                        try:
                            root.update_idletasks()
                        except Exception:
                            pass  # Ignore if window is destroyed
                        root.after(500, heartbeat)
                root.after(0, heartbeat)

                warmup_size = min(1, total)
                if warmup_size:
                    try:
                        batch = translated[:warmup_size]
                        cb = correct_text_batch_nllb(
                            batch, src_lang.get(), tgt_lang.get(), glossary=None,
                            translation_callback=lambda done, _batch_total, total=total: controller.update_post_progress(done, total)
                        )
                        corrected_all.extend(cb or [])
                        # Granular update for each line in warmup batch
                        for i in range(len(cb or [])):
                            controller.update_post_progress(len(corrected_all), total)
                    except Exception as e:
                        logging.exception(f"[do_post] Warm-up batch failed: {e}")

                batch_size = 8
                for start in range(warmup_size, total, batch_size):
                    end = min(start + batch_size, total)
                    batch = translated[start:end]
                    try:
                        cb = correct_text_batch_nllb(
                            batch, src_lang.get(), tgt_lang.get(),
                            translation_callback=lambda done, _batch_total, offset=start, total=total: controller.update_post_progress(done + offset, total)
                        )
                        corrected_all.extend(cb or [])
                        # Granular update for each line in this batch
                        for i in range(len(cb or [])):
                            controller.update_post_progress(len(corrected_all), total)
                    except Exception as e:
                        logging.exception(f"[do_post] Error in batch {start}-{end}: {e}")
                        # Skip this batch but continue
                        corrected_all.extend(batch)  # keep alignment by falling back to untranslated batch
                        for i in range(len(batch)):
                            controller.update_post_progress(len(corrected_all), total)

                if len(corrected_all) < total:
                    corrected_all.extend(translated[len(corrected_all):total])
                    for i in range(len(translated[len(corrected_all):total])):
                        controller.update_post_progress(len(corrected_all), total)


                def final_update_and_stop():
                    controller.update_post_progress(total, total)
                    stop_flag["stop"] = True
                    # Force UI to 100% and 'complete' after post-processing
                    controller.progress_var.set(100)
                    controller.status_label.config(text="100% | Time remaining: 00:00")
                    controller.post_label.config(text="Post-processing: complete")
                    controller.root.update_idletasks()
                root.after(0, final_update_and_stop)

                # Insert \N tags at user-specified word index as the final step
                n_wordidx = n_tag_wordidx.get()
                final_lines = [
                    insert_newline_tags_at_wordidx(line, n_count, n_wordidx)
                    for line, n_count in zip(corrected_all, n_tag_counts)
                ]
                for idx, (orig, trans, corr, final) in enumerate(zip(originals, translated, corrected_all, final_lines)):
                    try:
                        logger.log_entry(idx, orig, trans, final, tags_before=[], tags_after=[])
                    except Exception:
                        logging.exception(f"[do_post] Logging failed on line {idx+1}")
                try:
                    logger.write_summary()
                except Exception:
                    logging.exception("[do_post] Failed writing summary")

                log_path = logger.get_log_path() if hasattr(logger, "get_log_path") else logger.log_txt
                review_fn = review_txt_translations if file_type.get() == "txt" else review_sub_translations
                root.after(0, review_fn, pristine_originals, final_lines, output_path, log_path)

            except Exception as e:
                logging.exception(f"[do_post] Unhandled exception: {e}")
                root.after(0, lambda: on_translation_error(e))
            finally:
                # Always ensure UI is reset and button is re-enabled
                root.after(0, lambda: start_btn.config(state="normal"))
                root.after(0, controller.reset)
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
        # Disable options during translation
        src_lang_menu.config(state="disabled")
        tgt_lang_menu.config(state="disabled")
        file_type_menu.config(state="disabled")
        polish_only_cb.config(state="disabled")
        n_tag_wordidx_spin.config(state="disabled")
        status_label.config(text="Starting translation…")
        threading.Thread(target=run_and_reset, daemon=True).start()

    def on_translation_success(out_path: str, log_path: str | None = None):
        start_btn.config(state="normal")
        # Re-enable options after translation
        src_lang_menu.config(state="normal")
        tgt_lang_menu.config(state="normal")
        file_type_menu.config(state="normal")
        polish_only_cb.config(state="normal")
        n_tag_wordidx_spin.config(state="normal")
        controller.reset()
        messagebox.showinfo("Success", f"Translated file saved to:\n{out_path}")
        if log_path:
            messagebox.showinfo("Success", f"Log file saved to:\n{log_path}")

    def on_translation_error(err):
        start_btn.config(state="normal")
        # Re-enable options after error
        src_lang_menu.config(state="normal")
        tgt_lang_menu.config(state="normal")
        file_type_menu.config(state="normal")
        polish_only_cb.config(state="normal")
        status_label.config(text="Error")
        messagebox.showerror("Translation Failed", str(err))
        controller.reset()

    start_btn = tk.Button(root, text="Start Translation", command=start_translation_thread)
    start_btn.grid(row=10, column=0, columnspan=3, pady=10)

    root.mainloop()