import logging
from tkinter import filedialog, messagebox, ttk
import threading
import os, time
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
    tk.Entry(root, textvariable=file_path, width=40)
    browse_file_entry = tk.Entry(root, textvariable=file_path, width=40)
    browse_file_entry.grid(row=0, column=1, padx=5)
    tk.Button(root, text="Browse", command=lambda: browse_file())
    browse_file_btn = tk.Button(root, text="Browse", command=lambda: browse_file())
    browse_file_btn.grid(row=0, column=2)

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

    n_tag_wordidx_label = tk.Label(root, text="\\N tag word index:")
    n_tag_wordidx_label.grid(row=5, column=0, sticky="w")
    n_tag_wordidx_spin = tk.Spinbox(root, from_=0, to=50, textvariable=n_tag_wordidx, width=5)
    n_tag_wordidx_spin.grid(row=5, column=2, sticky="w")
    rigid_label = tk.Label(root, text="I would advise you to use a rigid value", font=("Arial", 10, "bold"))
    rigid_label.grid(row=5, column=1, sticky="w")
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
            n_tag_wordidx_label.grid_remove()
            n_tag_wordidx_spin.grid_remove()
            rigid_label.grid_remove()
        elif file_type.get() == "ass":
            n_tag_wordidx_spin.grid()
            rigid_label.grid()
            n_tag_wordidx_label.grid()
            formatting_cb.grid_remove()
            preview_btn.grid_remove()
        elif file_type.get() == "srt":
            formatting_cb.grid_remove()
            preview_btn.grid_remove()
            n_tag_wordidx_spin.grid_remove()
            n_tag_wordidx_label.grid_remove()
            rigid_label.grid_remove()
        else:
            formatting_cb.grid_remove()
            preview_btn.grid_remove()
            n_tag_wordidx_spin.grid_remove()
            n_tag_wordidx_label.grid_remove()
            rigid_label.grid_remove()

    file_type.trace_add("write", update_formatting_widgets)
    update_formatting_widgets()

    # ─── Translation Parameters ───────────────────────────────────────────────────
    # Advanced translation settings frame
    advanced_frame = tk.LabelFrame(root, text="Advanced Translation Parameters", padx=5, pady=5)
    advanced_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
    
    # Parameter validation functions
    def validate_beams(value):
        try:
            val = int(value)
            return 1 <= val <= 10
        except:
            return False
    
    def validate_penalty_temp(value):
        try:
            val = float(value)
            return 0.1 <= val <= 2.0
        except:
            return False
    
    def validate_batch_size(value):
        try:
            val = int(value)
            return 1 <= val <= 32
        except:
            return False
    
    # Register validation commands
    vcmd_beams = (root.register(validate_beams), '%P')
    vcmd_penalty_temp = (root.register(validate_penalty_temp), '%P')
    vcmd_batch = (root.register(validate_batch_size), '%P')
    
    # Beam search parameters
    num_beams_var = tk.IntVar(value=3)
    tk.Label(advanced_frame, text="Number of Beams:").grid(row=0, column=0, sticky="w")
    num_beams_spin = tk.Spinbox(advanced_frame, from_=1, to=10, textvariable=num_beams_var, 
                               width=5, validate='key', validatecommand=vcmd_beams)
    num_beams_spin.grid(row=0, column=1, sticky="w")
    tk.Label(advanced_frame, text="(1-10, higher=better quality, slower)", font=("Arial", 8)).grid(row=0, column=2, sticky="w")
    
    # Length penalty
    length_penalty_var = tk.DoubleVar(value=1.0)
    tk.Label(advanced_frame, text="Length Penalty:").grid(row=1, column=0, sticky="w")
    length_penalty_spin = tk.Spinbox(advanced_frame, from_=0.1, to=2.0, increment=0.1, 
                                   textvariable=length_penalty_var, width=8, format="%.1f",
                                   validate='key', validatecommand=vcmd_penalty_temp)
    length_penalty_spin.grid(row=1, column=1, sticky="w")
    tk.Label(advanced_frame, text="(0.1-2.0, >1.0=longer, <1.0=shorter)", font=("Arial", 8)).grid(row=1, column=2, sticky="w")
    
    # Temperature and sampling
    temperature_var = tk.DoubleVar(value=1.0)
    do_sample_var = tk.BooleanVar(value=False)
    
    tk.Label(advanced_frame, text="Temperature:").grid(row=2, column=0, sticky="w")
    temperature_spin = tk.Spinbox(advanced_frame, from_=0.1, to=2.0, increment=0.1,
                                textvariable=temperature_var, width=8, format="%.1f",
                                validate='key', validatecommand=vcmd_penalty_temp)
    temperature_spin.grid(row=2, column=1, sticky="w")
    tk.Label(advanced_frame, text="(0.1-2.0, higher=more creative)", font=("Arial", 8)).grid(row=2, column=2, sticky="w")
    
    sampling_cb = tk.Checkbutton(advanced_frame, text="Enable Sampling (uses temperature)", 
                               variable=do_sample_var)
    sampling_cb.grid(row=3, column=0, columnspan=2, sticky="w")
    
    # Top-k and Top-p parameters (only for sampling)
    top_k_var = tk.IntVar(value=50)
    top_p_var = tk.DoubleVar(value=0.9)
    
    tk.Label(advanced_frame, text="Top-K:").grid(row=4, column=0, sticky="w")
    top_k_spin = tk.Spinbox(advanced_frame, from_=1, to=100, textvariable=top_k_var, width=5)
    top_k_spin.grid(row=4, column=1, sticky="w")
    tk.Label(advanced_frame, text="(1-100, sampling diversity)", font=("Arial", 8)).grid(row=4, column=2, sticky="w")
    
    tk.Label(advanced_frame, text="Top-P:").grid(row=5, column=0, sticky="w")
    top_p_spin = tk.Spinbox(advanced_frame, from_=0.1, to=1.0, increment=0.1,
                           textvariable=top_p_var, width=8, format="%.1f")
    top_p_spin.grid(row=5, column=1, sticky="w")
    tk.Label(advanced_frame, text="(0.1-1.0, nucleus sampling)", font=("Arial", 8)).grid(row=5, column=2, sticky="w")
    
    # Batch size
    batch_size_var = tk.IntVar(value=12)
    tk.Label(advanced_frame, text="Batch Size:").grid(row=6, column=0, sticky="w")
    batch_size_spin = tk.Spinbox(advanced_frame, from_=1, to=32, textvariable=batch_size_var, 
                                width=5, validate='key', validatecommand=vcmd_batch)
    batch_size_spin.grid(row=6, column=1, sticky="w")
    tk.Label(advanced_frame, text="(1-32, higher=faster, more memory)", font=("Arial", 8)).grid(row=6, column=2, sticky="w")
    
    # Grammar correction toggle
    enable_grammar_var = tk.BooleanVar(value=True)
    grammar_cb = tk.Checkbutton(advanced_frame, text="Enable Grammar Correction", 
                              variable=enable_grammar_var)
    grammar_cb.grid(row=7, column=0, columnspan=2, sticky="w")
    
    # Parameter presets with more impactful differences
    def apply_preset(preset_name):
        if preset_name == "quality":
            num_beams_var.set(8)  # Increased for better quality
            length_penalty_var.set(1.3)  # More aggressive length preference
            temperature_var.set(0.7)
            do_sample_var.set(False)  # Deterministic for consistency
            batch_size_var.set(6)  # Smaller batches for stability
            top_k_var.set(40)  # More focused sampling when enabled
            top_p_var.set(0.85)  # More conservative nucleus sampling
        elif preset_name == "speed":
            num_beams_var.set(1)  # Greedy decoding for maximum speed
            length_penalty_var.set(1.0)  # Neutral
            temperature_var.set(1.0)
            do_sample_var.set(False)
            batch_size_var.set(20)  # Large batches for speed
            top_k_var.set(50)  # Default values
            top_p_var.set(0.9)
        elif preset_name == "creative":
            num_beams_var.set(4)  # Moderate beams
            length_penalty_var.set(0.8)  # Prefer shorter, punchier translations
            temperature_var.set(1.4)  # Higher creativity
            do_sample_var.set(True)  # Enable sampling for variety
            batch_size_var.set(10)
            top_k_var.set(60)  # More diverse sampling
            top_p_var.set(0.95)  # More permissive nucleus sampling
    
    # Preset buttons
    preset_frame = tk.Frame(advanced_frame)
    preset_frame.grid(row=8, column=0, columnspan=3, pady=5)
    
    tk.Label(preset_frame, text="Presets:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
    tk.Button(preset_frame, text="Quality", command=lambda: apply_preset("quality"), 
             bg="lightblue", width=8).pack(side=tk.LEFT, padx=2)
    tk.Button(preset_frame, text="Speed", command=lambda: apply_preset("speed"), 
             bg="lightgreen", width=8).pack(side=tk.LEFT, padx=2)
    tk.Button(preset_frame, text="Creative", command=lambda: apply_preset("creative"), 
             bg="lightyellow", width=8).pack(side=tk.LEFT, padx=2)
    
    # Reset to defaults button
    def reset_parameters():
        num_beams_var.set(3)
        length_penalty_var.set(1.0)
        temperature_var.set(1.0)
        do_sample_var.set(False)
        batch_size_var.set(12)
        enable_grammar_var.set(True)
        top_k_var.set(50)
        top_p_var.set(0.9)
    
    tk.Button(preset_frame, text="Reset", command=reset_parameters, 
             bg="lightcoral", width=8).pack(side=tk.LEFT, padx=2)
    
    # Help button
    def show_help():
        help_window = tk.Toplevel(root)
        help_window.title("Translation Parameters Help")
        help_window.geometry("600x500")
        help_window.resizable(True, True)
        
        help_text = """
🚀 ENHANCED TRANSLATION PARAMETERS GUIDE

📊 NUMBER OF BEAMS (1-10)
• Controls translation quality vs speed
• Higher values = better quality, slower translation
• Recommended: 3 (balanced), 8 (high quality), 1 (fast)

📏 LENGTH PENALTY (0.1-2.0)
• Controls output length preference
• 1.0 = neutral, >1.0 = prefer longer, <1.0 = prefer shorter
• For subtitles: 0.8-1.2 works well
• Quality preset uses 1.3 for more detailed translations

🌡️ TEMPERATURE (0.1-2.0)
• Only used when "Enable Sampling" is checked
• Controls creativity/randomness in translation
• Lower = more consistent, Higher = more creative
• Recommended: 0.7-0.8 (quality), 1.4+ (creative)

🎲 ENABLE SAMPLING
• Unchecked = deterministic (same input = same output)
• Checked = uses temperature for varied, natural outputs
• Essential for Creative preset, disabled for Quality/Speed

🎯 TOP-K SAMPLING (1-100)
• Controls diversity of token selection during sampling
• Lower values = more focused, Higher = more diverse
• Only active when sampling is enabled
• Quality: 40, Creative: 60, Speed: 50 (default)

🎪 TOP-P NUCLEUS SAMPLING (0.1-1.0)
• Controls probability mass for token selection
• Lower = more conservative, Higher = more permissive
• Works with Top-K to fine-tune sampling behavior
• Quality: 0.85, Creative: 0.95, Speed: 0.9 (default)

📦 BATCH SIZE (1-32)
• Number of lines processed together
• Higher = faster but uses more memory
• Lower if you get out-of-memory errors
• Quality: 6, Speed: 20, Creative: 10

📝 GRAMMAR CORRECTION
• Applies additional LanguageTool grammar checking
• Includes Polish conjugation and inflection fixes
• May slow down processing but improves accuracy
• Especially effective for Polish verb/noun agreement

🎯 ENHANCED PRESETS:
• Quality: 8 beams, aggressive post-processing, Polish-aware corrections
• Speed: 1 beam, minimal processing, large batches for performance  
• Creative: 4 beams, sampling enabled, diverse output generation

💡 POLISH LANGUAGE TIPS:
• Quality preset includes enhanced Polish conjugation checking
• Grammar correction handles verb/noun/adjective agreement
• Longer sentences benefit from higher length penalties
• Use Creative preset for more natural, conversational Polish
        """
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, font=("Arial", 10), padx=10, pady=10)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = tk.Scrollbar(help_window, command=text_widget.yview)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)
    
    tk.Button(preset_frame, text="Help", command=show_help, 
             bg="lightsteelblue", width=8).pack(side=tk.LEFT, padx=2)

    # ─── Progress & Status ────────────────────────────────────────────────────────
    progress_var = tk.DoubleVar(value=0)
    ttk.Progressbar(
        root,
        orient="horizontal",
        length=400,
        mode="determinate",
        maximum=100,
        variable=progress_var
    ).grid(row=7, column=0, columnspan=3, pady=10)

    status_label = tk.Label(root, text="0%")
    status_label.grid(row=8, column=0, columnspan=3)

    translation_label = tk.Label(root, text="Translation: waiting")
    translation_label.grid(row=9, column=0, columnspan=3)

    post_label = tk.Label(root, text="Post-processing: waiting")
    post_label.grid(row=10, column=0, columnspan=3)

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
            import threading
            tool = language_tool_python.LanguageTool('pl-PL')
            preview = tk.Toplevel(root)
            preview.title("Podgląd błędów fleksyjnych/gramatycznych (LanguageTool)")
            preview.geometry("900x600")
            text = tk.Text(preview, wrap="word", font=("Courier", 10))
            text.pack(fill=tk.BOTH, expand=True)
            text.tag_config("err", foreground="red")
            text.tag_config("msg", foreground="orange")
            text.tag_config("ok", foreground="black")
            tk.Button(preview, text="Zamknij", command=preview.destroy).pack(pady=10)

            def check_lines():
                for idx, line in enumerate(lines):
                    matches = tool.check(line)
                    def insert_result():
                        if not text.winfo_exists():
                            return
                        if matches:
                            text.insert(tk.END, f"Linia {idx+1}: {line}\n", "err")
                            for m in matches:
                                text.insert(tk.END, f"  - {m.ruleId}: {m.message}\n", "msg")
                        else:
                            text.insert(tk.END, f"Linia {idx+1}: {line}\n", "ok")
                    text.after(0, insert_result)
            threading.Thread(target=check_lines, daemon=True).start()
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

        btn_frame = tk.Frame(review)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Approve and Save", command=approve_and_save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Preview Flexion/Grammar Errors", command=lambda: show_flexion_preview([e.get() for e in entries])).pack(side="left", padx=5)

    def review_sub_translations(orig_nonempty, trans, out_path, log_path):
        # After user approves, show flexion/grammar error preview
        def show_flexion_preview(lines):
            import language_tool_python
            import threading
            tool = language_tool_python.LanguageTool('pl-PL')
            preview = tk.Toplevel(root)
            preview.title("Podgląd błędów fleksyjnych/gramatycznych (LanguageTool)")
            preview.geometry("900x600")
            text = tk.Text(preview, wrap="word", font=("Courier", 10))
            text.pack(fill=tk.BOTH, expand=True)
            text.tag_config("err", foreground="red")
            text.tag_config("msg", foreground="orange")
            text.tag_config("ok", foreground="black")
            tk.Button(preview, text="Zamknij", command=preview.destroy).pack(pady=10)

            def check_lines():
                for idx, line in enumerate(lines):
                    matches = tool.check(line)
                    def insert_result():
                        if matches:
                            text.insert(tk.END, f"Linia {idx+1}: {line}\n", "err")
                            for m in matches:
                                text.insert(tk.END, f"  - {m.ruleId}: {m.message}\n", "msg")
                        else:
                            text.insert(tk.END, f"Linia {idx+1}: {line}\n", "ok")
                    text.after(0, insert_result)
            threading.Thread(target=check_lines, daemon=True).start()
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

        btn_frame = tk.Frame(review)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Approve and Save", command=approve_and_save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Preview Flexion/Grammar Errors", command=lambda: show_flexion_preview([e.get() for e in entries])).pack(side="left", padx=5)

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
            # Determine quality mode based on parameters
            if num_beams_var.get() >= 7:  # Quality preset
                quality_mode = "aggressive"
            elif num_beams_var.get() <= 1:  # Speed preset  
                quality_mode = "conservative"
            else:
                quality_mode = "balanced"
                
            # Translate grouped lines with user-selected parameters
            translated_groups = translate_with_context_nllb(
                grouped_lines,
                src_lang.get(),
                tgt_lang.get(),
                model,
                tokenizer,
                device,
                beams=num_beams_var.get(),
                batch_size=batch_size_var.get(),
                polish_only=polish_only.get(),
                translation_callback=controller.update_translation_progress,
                length_penalty=length_penalty_var.get(),
                temperature=temperature_var.get(),
                do_sample=do_sample_var.get(),
                top_k=top_k_var.get(),
                top_p=top_p_var.get(),
                quality_mode=quality_mode
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
        
        # Ensure translation phase is complete before starting post-processing
        root.after(0, controller.show_post_start)

        def do_post():
            try:
                # Warm-up correction models AFTER post-processing officially starts
                try:
                    warmup_sentence = (
                        "To jest testowe zdanie." if tgt_lang.get().lower() == "pl"
                        else "This is a test sentence."
                    )
                    correct_text_batch_nllb([warmup_sentence], src_lang.get(), tgt_lang.get(),
                                           enable_grammar_correction=enable_grammar_var.get())
                except Exception as warm_err:
                    logging.warning(f"[prewarm] Correction warm‑up failed: {warm_err}")
                
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
                            translation_callback=lambda done, _batch_total, total=total: controller.update_post_progress(done, total),
                            enable_grammar_correction=enable_grammar_var.get()
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
                            translation_callback=lambda done, _batch_total, offset=start, total=total: controller.update_post_progress(done + offset, total),
                            enable_grammar_correction=enable_grammar_var.get()
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

                # Restore placeholder tags after post-processing
                restored_placeholders = [
                    restore_tags_from_placeholders(corrected_all[i], placeholder_maps[i])
                    for i in range(len(corrected_all))
                ]
                
                # Apply subtitle style/tone adjustment according to architecture
                from text_tools import adjust_subtitle_style_tone, insert_newline_tags_contextaware, clean_duplicate_newline_tags
                import re  # For tag detection
                style_adjusted = []
                for line in restored_placeholders:
                    adjusted = adjust_subtitle_style_tone(line, tgt_lang.get())
                    style_adjusted.append(adjusted)

                # Context-aware \N tag reinsertion as the final step (following architecture)
                n_wordidx = n_tag_wordidx.get()
                final_lines = []
                for i, (line, n_count) in enumerate(zip(style_adjusted, n_tag_counts)):
                    # Debug: Check what we're working with
                    existing_tags = len(re.findall(r'\\[Nn]', line))
                    
                    # Safety check: if line already contains \N tags, don't add more
                    if existing_tags > 0:
                        final_line = line  # Already has tags, don't modify
                        logging.debug(f"[tag_insert] Line {i} already has {existing_tags} tags, skipping insertion")
                    elif n_count > 0:
                        if n_wordidx == 0:
                            # Use context-aware placement (following architecture)
                            final_line = insert_newline_tags_contextaware(line, n_count, prefer_punctuation=True)
                            logging.debug(f"[tag_insert] Line {i}: context-aware insertion of {n_count} tags")
                        else:
                            # Use word index-based insertion
                            final_line = insert_newline_tags_at_wordidx(line, n_count, n_wordidx)
                            logging.debug(f"[tag_insert] Line {i}: word-index insertion of {n_count} tags at position {n_wordidx}")
                    else:
                        final_line = line
                        logging.debug(f"[tag_insert] Line {i}: no tags to insert (n_count={n_count})")
                    
                    # Additional safety check after insertion
                    final_tags = len(re.findall(r'\\[Nn]', final_line))
                    if final_tags > n_count and n_count > 0:
                        logging.warning(f"[tag_insert] Line {i}: More tags than expected! Expected: {n_count}, Found: {final_tags}")
                        # If we have too many tags, clean them up
                        final_line = clean_duplicate_newline_tags(final_line)
                    
                    final_lines.append(final_line)
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
        browse_file_entry.config(state="disabled")
        browse_file_btn.config(state="disabled")
        start_btn.config(state="disabled")
        # Disable options during translation
        src_lang_menu.config(state="disabled")
        tgt_lang_menu.config(state="disabled")
        file_type_menu.config(state="disabled")
        polish_only_cb.config(state="disabled")
        
        n_tag_wordidx_spin.config(state="disabled")
        status_label.config(text="Starting translation…")
        
        threading.Thread(target=run_and_reset, daemon=True).start()

    def on_translation_success(out_path: str, log_path: str | None = None, start_time: float | None = None):
        browse_file_entry.config(state="normal")
        browse_file_btn.config(state="normal")
        start_btn.config(state="normal")
        # Re-enable options after translation
        src_lang_menu.config(state="normal")
        tgt_lang_menu.config(state="normal")
        file_type_menu.config(state="normal")
        polish_only_cb.config(state="normal")
        n_tag_wordidx_spin.config(state="normal")
        if start_time is not None:
            duration = time.time() - start_time
            msg = f"Translated file saved to:\n{out_path}\n\nTime taken: {duration:.1f} seconds"
        else:
            msg = f"Translated file saved to:\n{out_path}"
        controller.reset()
        messagebox.showinfo("Success", msg)
        if log_path:
            messagebox.showinfo("Success", f"Log file saved to:\n{log_path}")

    def on_translation_error(err):
        start_btn.config(state="normal")
        browse_file_entry.config(state="normal")
        browse_file_btn.config(state="normal")
        # Re-enable options after error
        src_lang_menu.config(state="normal")
        tgt_lang_menu.config(state="normal")
        file_type_menu.config(state="normal")
        polish_only_cb.config(state="normal")
        status_label.config(text="Error")
        messagebox.showerror("Translation Failed", str(err))
        controller.reset()

    start_btn = tk.Button(root, text="Start Translation", command=start_translation_thread)
    start_btn.grid(row=11, column=0, columnspan=3, pady=10)

    root.mainloop()