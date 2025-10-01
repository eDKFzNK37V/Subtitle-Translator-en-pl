#!/usr/bin/env python3
"""
Simplified Subtitle Translator - NLLB Model
Supports .ass, .srt, and .txt file formats
Combined CLI and GUI in single file
"""

import os
import sys
import re
import argparse
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Tuple, Optional

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    from tqdm import tqdm
except ImportError as e:
    print(f"Error: Missing dependencies - {e}")
    print("Please install: pip install torch transformers tqdm")
    sys.exit(1)


# ============================================================================
# Translation Core
# ============================================================================

class SubtitleTranslator:
    """Simple NLLB-based translator for subtitles."""
    
    LANG_CODES = {
        'en': 'eng_Latn',
        'pl': 'pol_Latn',
        'ja': 'jpn_Jpan',
        'fr': 'fra_Latn',
        'de': 'deu_Latn',
    }
    
    TAG_PATTERN = re.compile(r'(\{[^}]*\}|\\[NnHh])')
    
    def __init__(self, model_name: str = "facebook/nllb-200-3.3B", batch_size: int = 8, num_beams: int = 2):
        """Initialize translator with NLLB model."""
        print(f"Loading model: {model_name}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        self.batch_size = batch_size
        self.num_beams = num_beams
        print("Model loaded!")
    
    def protect_tags(self, text: str) -> Tuple[str, List[str]]:
        """Replace tags with placeholders."""
        tags = []
        
        def replacer(match):
            tags.append(match.group(0))
            return f"<TAG{len(tags)-1}>"
        
        protected = self.TAG_PATTERN.sub(replacer, text)
        
        # Debug logging
        if tags:
            print(f"[TAG DEBUG] protect_tags:")
            print(f"  Input:     {repr(text)}")
            print(f"  Protected: {repr(protected)}")
            print(f"  Tags:      {tags}")
        
        return protected, tags
    
    def restore_tags(self, text: str, tags: List[str]) -> str:
        """Restore tags from placeholders."""
        original_text = text
        for i, tag in enumerate(tags):
            text = text.replace(f"<TAG{i}>", tag)
        # Clean any remaining placeholders
        text = re.sub(r'<TAG\d+>', '', text)
        
        # Debug logging
        if tags:
            print(f"[TAG DEBUG] restore_tags:")
            print(f"  Input:    {repr(original_text)}")
            print(f"  Tags:     {tags}")
            print(f"  Restored: {repr(text)}")
        
        return text
    
    def insert_n_tags(self, text: str, n_count: int, word_idx: int = 0) -> str:
        r"""Insert \N tags at specified word index."""
        if n_count <= 0 or not text.strip():
            return text
        
        words = text.split()
        if len(words) < 2:
            return text
        
        # Use middle if word_idx is 0 or out of range
        if word_idx <= 0 or word_idx >= len(words):
            word_idx = len(words) // 2
        
        # Insert \N tags
        for _ in range(n_count):
            if word_idx < len(words):
                words.insert(word_idx, '\\N')
                word_idx += 1
        
        return ' '.join(words)
    
    def _write_translation_log(self, log_path: str, originals: List[str], translations: List[str]):
        """Write translation log file with original and translated text side-by-side."""
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("TRANSLATION LOG\n")
            f.write("=" * 100 + "\n\n")
            
            for i, (orig, trans) in enumerate(zip(originals, translations), 1):
                f.write(f"[Line {i}]\n")
                f.write(f"Original:    {orig}\n")
                f.write(f"Translation: {trans}\n")
                f.write("-" * 100 + "\n\n")
            
            f.write("=" * 100 + "\n")
            f.write(f"Total lines: {len(originals)}\n")
        
        print(f"Translation log saved to: {log_path}")
    
    def translate(self, texts: List[str], src_lang: str, tgt_lang: str,
                  batch_size: Optional[int] = None, num_beams: Optional[int] = None, progress_callback=None) -> List[str]:
        """Translate a list of texts."""
        src_code = self.LANG_CODES.get(src_lang, src_lang)
        tgt_code = self.LANG_CODES.get(tgt_lang, tgt_lang)
        self.tokenizer.src_lang = src_code
        tgt_id = self.tokenizer.convert_tokens_to_ids(tgt_code)
        results = []
        total = len(texts)
        batch_size = batch_size if batch_size is not None else self.batch_size
        num_beams = num_beams if num_beams is not None else self.num_beams
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            encoded = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=256
            ).to(self.device)
            with torch.no_grad():
                generated = self.model.generate(
                    **encoded,
                    forced_bos_token_id=tgt_id,
                    max_length=256,
                    num_beams=num_beams,
                    early_stopping=True
                )
            translated = self.tokenizer.batch_decode(generated, skip_special_tokens=True)
            results.extend(translated)
            if progress_callback:
                progress_callback(min(i + batch_size, total), total)
        return results
    
    def translate_ass_file(self, input_path: str, src_lang: str, tgt_lang: str,
                           n_tag_idx: int = 0, progress_callback=None) -> Tuple[str, List[str], List[str]]:
        """Translate .ass file."""
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        # Separate header and dialogue
        header = []
        dialogues = []
        texts_to_translate = []
        original_texts = []
        all_tags = []  # Store tags for each line
        n_tag_counts = []
        
        in_events = False
        for line in lines:
            if line.strip().startswith('[Events]'):
                in_events = True
                header.append(line)
            elif in_events and line.startswith('Dialogue:'):
                dialogues.append(line)
                # Extract text (last field after 9 commas)
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    text = parts[9].rstrip('\n')
                    original_texts.append(text)
                    
                    # Count \N tags
                    n_count = len(re.findall(r'\\N', text, re.IGNORECASE))
                    n_tag_counts.append(n_count)
                    
                    # Remove \N for translation
                    clean_text = re.sub(r'\\N', ' ', text, flags=re.IGNORECASE)
                    
                    # Protect tags and store them
                    protected, tags = self.protect_tags(clean_text)
                    all_tags.append(tags)
                    texts_to_translate.append(protected)
            else:
                header.append(line)
        
        # Translate
        translated = self.translate(texts_to_translate, src_lang, tgt_lang,
                                   progress_callback=progress_callback)
        
        # Restore tags and \N
        final_texts = []
        for i, trans in enumerate(translated):
            # Restore the original tags that were protected
            with_tags = self.restore_tags(trans, all_tags[i])
            
            # Insert \N tags
            with_n = self.insert_n_tags(with_tags, n_tag_counts[i], n_tag_idx)
            
            final_texts.append(with_n)
        
        # Create log file
        log_path = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}_log.txt'
        self._write_translation_log(log_path, original_texts, final_texts)
        
        # Rebuild file
        output_lines = header[:]
        for i, dialogue in enumerate(dialogues):
            parts = dialogue.split(',', 9)
            if len(parts) >= 10:
                parts[9] = final_texts[i] + '\n'
                output_lines.append(','.join(parts))
            else:
                output_lines.append(dialogue)
        
        # Save
        output_path = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}.ass'
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.writelines(output_lines)
        
        return output_path, original_texts, final_texts
    
    def translate_srt_file(self, input_path: str, src_lang: str, tgt_lang: str,
                           progress_callback=None) -> Tuple[str, List[str], List[str]]:
        """Translate .srt file."""
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # Split into subtitle blocks
        blocks = re.split(r'\n\s*\n', content.strip())
        
        texts_to_translate = []
        original_texts = []
        all_tags = []  # Store tags for each line
        block_data = []
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # index, timestamp, text...
                index_line = lines[0]
                time_line = lines[1]
                text_lines = lines[2:]
                text = '\n'.join(text_lines)
                
                original_texts.append(text)
                
                # Protect tags and store them
                protected, tags = self.protect_tags(text)
                all_tags.append(tags)
                texts_to_translate.append(protected)
                block_data.append((index_line, time_line))
        
        # Translate
        translated = self.translate(texts_to_translate, src_lang, tgt_lang,
                                   progress_callback=progress_callback)
        
        # Restore tags using the stored tags from before translation
        final_texts = []
        for i, trans in enumerate(translated):
            with_tags = self.restore_tags(trans, all_tags[i])
            final_texts.append(with_tags)
        
        # Create log file
        log_path = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}_log.txt'
        self._write_translation_log(log_path, original_texts, final_texts)
        
        # Rebuild file
        output_blocks = []
        for i, (idx, time) in enumerate(block_data):
            output_blocks.append(f"{idx}\n{time}\n{final_texts[i]}")
        
        output_content = '\n\n'.join(output_blocks) + '\n'
        
        # Save
        output_path = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}.srt'
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(output_content)
        
        return output_path, original_texts, final_texts
    
    def translate_txt_file(self, input_path: str, src_lang: str, tgt_lang: str,
                           progress_callback=None) -> Tuple[str, List[str], List[str]]:
        """Translate .txt file."""
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        # Only translate non-empty lines
        texts_to_translate = []
        original_texts = []
        line_indices = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.isdigit():
                original_texts.append(stripped)
                texts_to_translate.append(stripped)
                line_indices.append(i)
        
        # Translate
        translated = self.translate(texts_to_translate, src_lang, tgt_lang,
                                   progress_callback=progress_callback)
        
        # Create log file
        log_path = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}_log.txt'
        self._write_translation_log(log_path, original_texts, translated)
        
        # Rebuild file
        output_lines = lines[:]
        for i, idx in enumerate(line_indices):
            # Preserve formatting
            leading = len(lines[idx]) - len(lines[idx].lstrip(' '))
            trailing = len(lines[idx]) - len(lines[idx].rstrip(' '))
            has_newline = lines[idx].endswith('\n')
            
            output_lines[idx] = (' ' * leading) + translated[i] + (' ' * trailing)
            if has_newline:
                output_lines[idx] += '\n'
        
        # Save
        output_path = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}.txt'
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.writelines(output_lines)
        
        return output_path, original_texts, translated


# ============================================================================
# GUI
# ============================================================================

def run_gui():
    """Run the simplified GUI."""
    
    root = tk.Tk()
    root.title("Subtitle Translator (NLLB)")
    root.geometry("580x280")
    
    # Variables
    file_path = tk.StringVar()
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")
    file_type = tk.StringVar(value="ass")
    n_tag_wordidx = tk.IntVar(value=0)
    batch_size_var = tk.IntVar(value=8)
    num_beams_var = tk.IntVar(value=2)
    
    LANG_OPTIONS = ["en", "pl", "ja", "fr", "de"]
    FILE_TYPES = ["ass", "srt", "txt"]
    
    translator = None
    
    # File Selection Group
    file_frame = tk.LabelFrame(root, text="File Selection", padx=5, pady=5)
    file_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
    tk.Label(file_frame, text="File:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
    tk.Entry(file_frame, textvariable=file_path, width=48).grid(row=0, column=1, padx=2, pady=2)
    
    def browse_file():
        filename = filedialog.askopenfilename(
            title="Select subtitle file",
            filetypes=[
                ("Subtitle files", "*.ass *.srt *.txt"),
                ("All files", "*.*")
            ]
        )
        if filename:
            file_path.set(filename)
            # Auto-detect file type
            ext = filename.rsplit('.', 1)[-1].lower()
            if ext in FILE_TYPES:
                file_type.set(ext)
    
    tk.Button(file_frame, text="Browse", command=browse_file, width=8).grid(row=0, column=2, padx=2, pady=2)
    
    # Language & Format Group
    lang_frame = tk.LabelFrame(root, text="Translation Settings", padx=5, pady=5)
    lang_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
    tk.Label(lang_frame, text="Source:").grid(row=0, column=0, sticky="w", padx=2)
    tk.OptionMenu(lang_frame, src_lang, *LANG_OPTIONS).grid(row=0, column=1, sticky="w", padx=2)
    
    tk.Label(lang_frame, text="Target:").grid(row=0, column=2, sticky="w", padx=2)
    tk.OptionMenu(lang_frame, tgt_lang, *LANG_OPTIONS).grid(row=0, column=3, sticky="w", padx=2)
    
    tk.Label(lang_frame, text="Format:").grid(row=0, column=4, sticky="w", padx=2)
    tk.OptionMenu(lang_frame, file_type, *FILE_TYPES).grid(row=0, column=5, sticky="w", padx=2)
    
    # Advanced Options Group
    adv_frame = tk.LabelFrame(root, text="Advanced Options", padx=5, pady=5)
    adv_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
    tk.Label(adv_frame, text=r"\N index:").grid(row=0, column=0, sticky="w", padx=2)
    tk.Spinbox(adv_frame, from_=0, to=50, textvariable=n_tag_wordidx, width=6).grid(row=0, column=1, sticky="w", padx=2)
    
    tk.Label(adv_frame, text="Batch:").grid(row=0, column=2, sticky="w", padx=(10,2))
    tk.Spinbox(adv_frame, from_=1, to=64, textvariable=batch_size_var, width=6).grid(row=0, column=3, sticky="w", padx=2)
    
    tk.Label(adv_frame, text="Beams:").grid(row=0, column=4, sticky="w", padx=(10,2))
    tk.Spinbox(adv_frame, from_=1, to=10, textvariable=num_beams_var, width=6).grid(row=0, column=5, sticky="w", padx=2)

    # Progress
    progress_label = tk.Label(root, text="Translation: 0%", font=("Arial", 9))
    progress_label.grid(row=3, column=0, columnspan=3, pady=2)

    status_label = tk.Label(root, text="Ready", font=("Arial", 9, "bold"))
    status_label.grid(row=4, column=0, columnspan=3, pady=2)

    start_btn = tk.Button(root, text="Start Translation", width=20, bg="#4CAF50", fg="white")
    start_btn.grid(row=5, column=0, columnspan=3, pady=10)
    
    def update_progress(current, total):
        """Update progress display."""
        if total > 0:
            pct = int((current / total) * 100)
            progress_label.config(text=f"Translation: {pct}%")
            root.update_idletasks()
    
    def show_review(originals, translations, output_path):
        """Show review window with side-by-side layout."""
        review_win = tk.Toplevel(root)
        review_win.title("Review Translations")
        review_win.geometry("1200x700")
        
        # Header frame
        header_frame = tk.Frame(review_win)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Header labels
        tk.Label(header_frame, text="Original", font=("Arial", 10, "bold"), width=50, anchor="w").pack(side=tk.LEFT, padx=5)
        tk.Label(header_frame, text="Translation", font=("Arial", 10, "bold"), width=50, anchor="w").pack(side=tk.LEFT, padx=5)
        
        # Scrollable frame
        frame = tk.Frame(review_win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(frame)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Populate rows with two-column layout
        entry_widgets = []
        for i, (orig, trans) in enumerate(zip(originals, translations)):
            # Row number
            tk.Label(scrollable_frame, text=f"{i+1}", font=("Arial", 9), width=3, anchor="e").grid(
                row=i, column=0, sticky="ne", padx=(0, 5), pady=2)
            
            # Original text (left column)
            orig_text = tk.Text(scrollable_frame, width=50, height=2, wrap=tk.WORD, font=("Arial", 9))
            orig_text.insert("1.0", orig)
            orig_text.config(state="disabled", bg="#f0f0f0")
            orig_text.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            
            # Translation (right column - editable)
            trans_entry = tk.Entry(scrollable_frame, width=50, font=("Arial", 9))
            trans_entry.insert(0, trans)
            trans_entry.grid(row=i, column=2, sticky="ew", padx=5, pady=2)
            entry_widgets.append(trans_entry)
        
        # Configure grid weights for resizing
        scrollable_frame.grid_columnconfigure(1, weight=1)
        scrollable_frame.grid_columnconfigure(2, weight=1)
        
        def save_and_close():
            edited = [e.get() for e in entry_widgets]
            # Save edited translations
            # (File already saved, this would be for re-saving edits)
            review_win.destroy()
            messagebox.showinfo("Success", f"Translation completed!\nSaved to: {output_path}")
            reset_ui()
        
        def cancel_translation():
            """Cancel translation and reset UI."""
            review_win.destroy()
            messagebox.showinfo("Cancelled", "Translation was cancelled.")
            reset_ui()
        
        # Handle window close (X button)
        review_win.protocol("WM_DELETE_WINDOW", cancel_translation)
        
        # Bottom button frame
        btn_frame = tk.Frame(review_win)
        btn_frame.pack(side=tk.BOTTOM, pady=10)
        tk.Button(btn_frame, text="Approve and Save", command=save_and_close, width=20, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=cancel_translation, width=15).pack(side=tk.LEFT, padx=5)
    
    def reset_ui():
        """Reset UI to initial state."""
        start_btn.config(state="normal")
        progress_label.config(text="Translation: 0%")
        status_label.config(text="Ready")
    
    def start_translation():
        """Start translation in background thread."""
        nonlocal translator
        
        path = file_path.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Please select a valid file")
            return
        
        if src_lang.get() == tgt_lang.get():
            messagebox.showerror("Error", "Source and target languages must be different")
            return
        
        start_btn.config(state="disabled")
        status_label.config(text="Loading model...")
        progress_label.config(text="Translation: 0%")
        
        def translate_thread():
            nonlocal translator
            try:
                # Load model if needed
                if translator is None:
                    translator = SubtitleTranslator(
                        batch_size=batch_size_var.get(),
                        num_beams=num_beams_var.get()
                    )

                status_label.config(text="Translating...")
                root.update_idletasks()

                # Translate based on file type
                ftype = file_type.get()
                if ftype == "ass":
                    output_path, originals, translations = translator.translate_ass_file(
                        path, src_lang.get(), tgt_lang.get(),
                        n_tag_wordidx.get(), update_progress
                    )
                elif ftype == "srt":
                    output_path, originals, translations = translator.translate_srt_file(
                        path, src_lang.get(), tgt_lang.get(), update_progress
                    )
                else:  # txt
                    output_path, originals, translations = translator.translate_txt_file(
                        path, src_lang.get(), tgt_lang.get(), update_progress
                    )

                status_label.config(text="Complete!")
                progress_label.config(text="Translation: 100%")

                # Show review window
                root.after(0, lambda: show_review(originals, translations, output_path))

            except Exception as e:
                import traceback
                error_msg = f"Translation failed:\n\n{str(e)}\n\n{traceback.format_exc()}"
                root.after(0, lambda: messagebox.showerror("Translation Error", error_msg))
                root.after(0, reset_ui)
        
        # Run in thread
        thread = threading.Thread(target=translate_thread, daemon=True)
        thread.start()
    
    start_btn.config(command=start_translation)
    
    root.mainloop()


# ============================================================================
# CLI
# ============================================================================

def run_cli():
    """Run CLI mode."""
    parser = argparse.ArgumentParser(description="Subtitle Translator CLI")
    parser.add_argument("input_file", help="Input subtitle file (.ass, .srt, or .txt)")
    parser.add_argument("--src", default="en", help="Source language (default: en)")
    parser.add_argument("--tgt", default="pl", help="Target language (default: pl)")
    parser.add_argument("--nwordix", type=int, default=0, help="Word index for \\N tag insertion (0=auto, .ass only)")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size (default: 8)")
    parser.add_argument("--num-beams", type=int, default=2, help="Beam search width (default: 2)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: File not found: {args.input_file}")
        sys.exit(1)
    
    # Detect file type
    ext = args.input_file.rsplit('.', 1)[-1].lower()
    if ext not in ['ass', 'srt', 'txt']:
        print(f"Error: Unsupported file type: {ext}")
        sys.exit(1)
    
    print(f"\nTranslating: {args.input_file}")
    print(f"Languages: {args.src} -> {args.tgt}")
    
    # Load translator
    translator = SubtitleTranslator(batch_size=args.batch_size, num_beams=args.num_beams)
    
    def progress_callback(current, total):
        pct = int((current / total) * 100)
        print(f"\rProgress: {current}/{total} ({pct}%)", end='', flush=True)
    
    # Translate
    try:
        if ext == 'ass':
            output_path, _, _ = translator.translate_ass_file(
                args.input_file, args.src, args.tgt,
                args.nwordix, progress_callback
            )
        elif ext == 'srt':
            output_path, _, _ = translator.translate_srt_file(
                args.input_file, args.src, args.tgt, progress_callback
            )
        else:  # txt
            output_path, _, _ = translator.translate_txt_file(
                args.input_file, args.src, args.tgt, progress_callback
            )
        
        print(f"\n\nSuccess! Saved to: {output_path}")
        
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # CLI mode if file argument provided
        run_cli()
    else:
        # GUI mode
        run_gui()
