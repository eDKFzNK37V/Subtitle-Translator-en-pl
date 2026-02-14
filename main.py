

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
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, BitsAndBytesConfig
    from tqdm import tqdm
    try:
        from peft import PeftModel
        PEFT_AVAILABLE = True
    except ImportError:
        PEFT_AVAILABLE = False
    try:
        import bitsandbytes
        BITSANDBYTES_AVAILABLE = True
    except ImportError:
        BITSANDBYTES_AVAILABLE = False
except ImportError as e:
    print(f"Error: Missing dependencies - {e}")
    print("Please install: pip install torch transformers tqdm peft")
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
    DEFAULT_MAX_NEW_TOKENS = 120
    LANG_MAX_NEW_TOKENS = {
        'pl': 150,
    }
    
    # Only match {\...} tags, not \N or similar linebreaks
    TAG_ONLY = re.compile(r"({\\.*?})")
    TAG_OR_ESCAPE = re.compile(r"({\\.*?})|(\\[NnHhRr])")
    
    def __init__(self, model_name: str = "facebook/nllb-200-3.3B", batch_size: int = 32, num_beams: int = 4, 
                 lora_adapter: Optional[str] = None, use_fp16: bool = True, use_quantization: bool = False,
                 quantization_bits: int = 4):
        """Initialize translator with NLLB model and optional LoRA adapter.
        
        Args:
            model_name: HuggingFace model name
            batch_size: Initial batch size (will be reduced on OOM)
            num_beams: Number of beams for beam search
            lora_adapter: Path to LoRA adapter directory
            use_fp16: Use FP16 (half precision) for faster inference
            use_quantization: Use quantization (4-bit or 8-bit)
            quantization_bits: Bits for quantization (4 or 8)
        """
        print(f"Loading model: {model_name}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        # Store optimization settings
        self.use_fp16 = use_fp16 and self.device == "cuda"
        self.use_quantization = use_quantization and self.device == "cuda"
        self.quantization_bits = quantization_bits
        self.initial_batch_size = batch_size
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Configure quantization if requested
        quantization_config = None
        if self.use_quantization:
            if not BITSANDBYTES_AVAILABLE:
                print("⚠️  Warning: bitsandbytes not available. Disabling quantization.")
                print("   Install with: pip install bitsandbytes")
                self.use_quantization = False
            else:
                print(f"Using {quantization_bits}-bit quantization")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=(quantization_bits == 4),
                    load_in_8bit=(quantization_bits == 8),
                    bnb_4bit_compute_dtype=torch.float16 if quantization_bits == 4 else None,
                )
        
        # Load model with quantization if enabled
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto" if self.use_quantization else None
        )
        
        # Apply LoRA adapter if provided
        if lora_adapter:
            if not PEFT_AVAILABLE:
                raise ImportError("peft is required for LoRA adapter support. Please install with: pip install peft")
            print(f"Loading LoRA adapter from: {lora_adapter}")
            self.model = PeftModel.from_pretrained(self.model, lora_adapter) # type: ignore
        
        # Move to device and optimize
        if not self.use_quantization:
            self.model.to(self.device)
            # Apply FP16 if requested and not using quantization
            if self.use_fp16:
                print("Using FP16 (half precision)")
                self.model = self.model.half()
        
        self.model.eval()
        
        # Enable TF32 for faster matmul on Ampere+ GPUs
        if self.device == "cuda" and torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            print("TF32 optimization enabled")
        
        self.batch_size = batch_size
        self.num_beams = num_beams
        print(f"Model loaded! (FP16: {self.use_fp16}, Quantized: {self.use_quantization})")

    @staticmethod
    def group_dialogues_by_speaker(dialogue_lines, enable_grouping=False):
            """
            Group consecutive dialogue lines by the same speaker (if names detected).
            Expects a list of ASS dialogue lines (strings).
            Returns a list of grouped dicts: {"name": ..., "lines": [...], "start": ..., "end": ...}
            If any name is missing, returns None (no grouping).
            
            Args:
                dialogue_lines: List of dialogue lines from .ass file
                enable_grouping: Whether to enable speaker-based grouping (default: False)
            
            NOTE: Grouping is disabled by default as it can cause issues with splitting
            translated text back into individual dialogue lines. Enable only for files
            with rich speaker names (e.g., anime with character names in each line).
            """
            # If grouping is disabled, return None to use line-by-line translation
            if not enable_grouping:
                return None
            
            # Grouping enabled - group by speaker
            grouped = []
            current = None
            for line in dialogue_lines:
                parts = line.split(",", 9)
                name = parts[4].strip() if len(parts) > 4 else ""
                text = parts[9] if len(parts) > 9 else ""
                start = parts[1] if len(parts) > 1 else ""
                end = parts[2] if len(parts) > 2 else ""
                if not name:
                    # If any name is missing, skip grouping entirely
                    return None
                if current and current["name"] == name:
                    current["lines"].append(text)
                    current["end"] = end
                else:
                    if current:
                        grouped.append(current)
                    current = {"name": name, "lines": [text], "start": start, "end": end}
            if current:
                grouped.append(current)
            return grouped
    
    def protect_tags(self, text: str) -> Tuple[str, list]:
        import time
        start = time.perf_counter()
        """
        Replace all tags/escapes with unique placeholders and return:
          clean_text, ph_map
        ph_map: list of tuples (placeholder, original_value, original_pos)
        """
        ph_map = []
        idx = 0

        def repl(m):
            nonlocal idx
            placeholder = f"<TAGPH_{idx}>"
            ph_map.append((placeholder, m.group(0), m.start()))
            idx += 1
            return placeholder

        # Use re.sub to directly replace tags/escapes with placeholders, preserving all other text
        clean_text = self.TAG_OR_ESCAPE.sub(repl, text)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        if elapsed > 10:
            print(f"[PROFILE] protect_tags: {elapsed:.2f} ms for {len(text)} chars")
        return clean_text, ph_map

    @classmethod
    def get_max_new_tokens(cls, tgt_lang: str, tgt_code: Optional[str] = None) -> int:
        lang_codes_rev = {value: key for key, value in cls.LANG_CODES.items()}
        short_lang = lang_codes_rev.get(tgt_lang, tgt_lang)
        short_code = lang_codes_rev.get(tgt_code, tgt_code) if tgt_code else None
        max_new_tokens = cls.LANG_MAX_NEW_TOKENS.get(short_lang)
        if max_new_tokens is not None:
            return max_new_tokens
        if short_code:
            max_new_tokens = cls.LANG_MAX_NEW_TOKENS.get(short_code)
            if max_new_tokens is not None:
                return max_new_tokens
        return cls.DEFAULT_MAX_NEW_TOKENS
    
    def restore_tags(self, translated: str, ph_map: list) -> str:
        """
        Replace placeholders in translated text with original tags/escapes.
        If a placeholder is missing (model dropped it), insert the tag at the
        closest possible position based on semantic similarity and word boundaries.
        """
        import re
        out = translated

        # First pass: replace placeholders that survived translation
        for placeholder, original, _pos in ph_map:
            if placeholder in out:
                out = out.replace(placeholder, original)

        # Only insert if the original tag is not already present in the string
        missing = []
        for (p, o, pos) in ph_map:
            if p not in translated and o not in out:
                missing.append((p, o, pos))
        missing.sort(key=lambda x: x[2])

        def find_optimal_insertion_point(text: str, original_pos: int, original_total_len: int) -> int:
            """
            Find the best insertion point using relative positioning and word boundaries.
            """
            if not text.strip():
                return 0
            # Calculate relative position (0.0 to 1.0)
            relative_pos = original_pos / max(original_total_len, 1)
            target_char = int(relative_pos * len(text))
            # Find nearest word boundary
            words = [(m.group(), m.start(), m.end()) for m in re.finditer(r'\S+', text)]
            if not words:
                return 0
            # Find the word closest to our target position
            best_insert = 0
            min_distance = float('inf')
            for i, (word, start, end) in enumerate(words):
                # Check both before and after this word
                distances = [
                    (abs(start - target_char), start),  # before word
                    (abs(end - target_char), end)       # after word
                ]
                for distance, pos in distances:
                    if distance < min_distance:
                        min_distance = distance
                        best_insert = pos
            return best_insert
        
        
        def insert_tag_with_smart_spacing(text: str, pos: int, tag: str) -> str:
            """
            Insert tag with intelligent spacing to avoid collisions.
            """
            if pos <= 0:
                # Insert at beginning
                if text and text[0].isalnum():
                    return tag + ' ' + text
                return tag + text
            elif pos >= len(text):
                # Insert at end  
                if text and text[-1].isalnum():
                    return text + ' ' + tag
                return text + tag
            else:
                # Insert in middle
                before_char = text[pos-1] if pos > 0 else ' '
                after_char = text[pos] if pos < len(text) else ' '
                space_before = ' ' if before_char.isalnum() else ''
                space_after = ' ' if after_char.isalnum() else ''
                return text[:pos] + space_before + tag + space_after + text[pos:]

        # Get original text length for relative positioning
        original_total_len = max([pos for _, _, pos in ph_map] + [len(translated)]) if ph_map else len(translated)
        for _placeholder, original, pos in missing:
            insert_at = find_optimal_insertion_point(out, pos, original_total_len)
            out = insert_tag_with_smart_spacing(out, insert_at, original)

        # Remove any leftover placeholders like <TAGPH_0>, < TAGPH_0>, etc.
        out = re.sub(r'<\s*TAGPH_\d+\s*>?', '', out)  # Remove all <TAGPH_n> variants with optional spaces and optional closing '>'
        return out
    
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
    
    def _write_translation_log(self, log_path: str, originals: List[str], translations: List[str], setup_info: Optional[dict] = None, duration: Optional[float] = None):
        """Write translation log file with original and translated text side-by-side, including setup info and duration."""
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("TRANSLATION LOG\n")
            f.write("=" * 100 + "\n\n")
            # Write setup info if provided
            if setup_info:
                f.write("Translation Setup:\n")
                for k, v in setup_info.items():
                    f.write(f"  {k}: {v}\n")
                f.write("\n")
            if duration is not None:
                f.write(f"Duration: {duration:.2f} seconds\n")
                f.write(f"Lines translated: {len(originals)}\n\n")
            for i, (orig, trans) in enumerate(zip(originals, translations), 1):
                f.write(f"[Line {i}]\n")
                f.write(f"Original:    {orig}\n")
                f.write(f"Translation: {trans}\n")
                f.write("-" * 100 + "\n\n")
            f.write("=" * 100 + "\n")
            f.write(f"Total lines: {len(originals)}\n")
        print(f"Translation log saved to: {log_path}")
    
    def translate(self, texts: List[str], src_lang: str, tgt_lang: str,
              batch_size: Optional[int] = None, num_beams: Optional[int] = None,
              progress_callback=None) -> List[str]:
        """
        Translate a list of subtitle lines (.ass or plain text).
        Preserves metadata and formatting tags, cleans spacing, and skips empty lines.
        Implements adaptive batch sizing with OOM handling.
        """

        src_code = self.LANG_CODES.get(src_lang, src_lang)
        tgt_code = self.LANG_CODES.get(tgt_lang, tgt_lang)
        self.tokenizer.src_lang = src_code
        tgt_id = self.tokenizer.convert_tokens_to_ids(tgt_code)
        max_new_tokens = self.get_max_new_tokens(tgt_lang, tgt_code)

        current_batch_size = batch_size or self.batch_size
        num_beams = num_beams or self.num_beams
        results = []
        total = len(texts)

        dialogue_pattern = re.compile(r'^(Dialogue:\s*\d+,\d+:\d+:\d+\.\d+,\d+:\d+:\d+\.\d+,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,)(.*)$')

        i = 0
        while i < total:
            batch = texts[i:i + current_batch_size]
            translatable_texts, metadata_prefixes, empty_flags = [], [], []

            for line in batch:
                if not line.strip():
                    metadata_prefixes.append("")
                    translatable_texts.append("")
                    empty_flags.append(True)
                    continue

                match = dialogue_pattern.match(line)
                if match:
                    prefix, dialogue_text = match.groups()
                    metadata_prefixes.append(prefix)
                    translatable_texts.append(dialogue_text.strip())
                else:
                    metadata_prefixes.append("")
                    translatable_texts.append(line.strip())

                empty_flags.append(False)

            # Filter out truly empty lines for efficiency
            non_empty_inputs = [t for t, e in zip(translatable_texts, empty_flags) if not e]
            if not non_empty_inputs:
                results.extend(["" for _ in batch])
                i += current_batch_size
                if progress_callback:
                    progress_callback(min(i, total), total)
                continue

            try:
                encoded = self.tokenizer(
                    non_empty_inputs,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512
                ).to(self.device)

                with torch.no_grad():
                    generated = self.model.generate(
                        **encoded,
                        forced_bos_token_id=tgt_id,
                        max_new_tokens=max_new_tokens,  # Use max_new_tokens instead of max_length
                        num_beams=num_beams,
                        early_stopping=True,
                        use_cache=True
                    )

                translated_batch = self.tokenizer.batch_decode(generated, skip_special_tokens=True)

                # Reinsert translated results
                idx = 0
                for prefix, was_empty in zip(metadata_prefixes, empty_flags):
                    if was_empty:
                        results.append("")
                        continue
                    translated_text = translated_batch[idx]
                    idx += 1

                    # Clean up spaces around tags and \N
                    translated_text = re.sub(r'\s*\\N\s*', r'\\N', translated_text)
                    translated_text = re.sub(r'\s*({\\[^}]+})\s*', r'\1', translated_text)

                    final_line = prefix + translated_text if prefix else translated_text
                    results.append(final_line)

                # Success - move to next batch
                i += current_batch_size
                if progress_callback:
                    progress_callback(min(i, total), total)

            except (RuntimeError, torch.cuda.OutOfMemoryError) as e:
                if "out of memory" in str(e).lower() and current_batch_size > 1:
                    # OOM occurred - reduce batch size and retry
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    current_batch_size = max(1, current_batch_size // 2)
                    print(f"\n⚠️  Reduced batch size to {current_batch_size} due to OOM.")
                    # Don't increment i - retry this batch with smaller size
                    # Clear results that were partially added
                    results = results[:i]
                else:
                    # Non-OOM error or batch size is already 1
                    raise

        return results
    

    def _get_unique_path(self, base_path: str, ext: str) -> str:
        """Return a unique file path by appending a number if needed."""
        path = f"{base_path}{ext}"
        i = 1
        while os.path.exists(path):
            path = f"{base_path}_{i}{ext}"
            i += 1
        return path

    def translate_ass_file(self, input_path: str, src_lang: str, tgt_lang: str,
                           n_tag_idx: int = 0, enable_grouping: bool = False, 
                           progress_callback=None, preparing_callback=None) -> Tuple[str, List[str], List[str]]:
        """Translate .ass file, optionally grouping by speaker.
        
        Args:
            input_path: Path to input .ass file
            src_lang: Source language code
            tgt_lang: Target language code
            n_tag_idx: Word index for \\N tag insertion
            enable_grouping: Enable speaker-based grouping (default: False)
            progress_callback: Callback for progress updates
            preparing_callback: Callback for preparation status
        """
        import time
        start_time = time.time()
        if preparing_callback:
            preparing_callback("Reading and parsing .ass file... (Preparation time depends on the amount of lines in the file)")
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

        # Separate header and dialogue
        import time as _time
        _parse_start = _time.perf_counter()
        header = []
        dialogues = []
        in_events = False
        for line in lines:
            if line.strip().startswith('[Events]'):
                in_events = True
                header.append(line)
            elif in_events and line.startswith('Dialogue:'):
                dialogues.append(line)
            else:
                header.append(line)
        _parse_elapsed = (_time.perf_counter() - _parse_start) * 1000
        print(f"[PROFILE] ASS header/dialogue split: {_parse_elapsed:.2f} ms for {len(lines)} lines")
        if preparing_callback:
            preparing_callback("Preparing translation batches... (Preparation time depends on the amount of lines in the file)")

        # Try grouping by speaker (if enabled)
        grouped = self.group_dialogues_by_speaker(dialogues, enable_grouping=enable_grouping)

        # Prepare output/log base paths
        def get_unique_path(base_path, ext):
            path = f"{base_path}{ext}"
            i = 1
            while os.path.exists(path):
                path = f"{base_path}_{i}{ext}"
                i += 1
            return path
        base = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}'
        out_path = get_unique_path(base, '.ass')
        log_path = get_unique_path(base, '_log.txt')

        # Gather setup info
        setup_info = {
            "Model": getattr(self.model, 'name_or_path', str(type(self.model))),
            "Batch size": self.batch_size,
            "Num beams": self.num_beams,
            "Device": self.device,
            "FP16 mode": self.use_fp16,
            "Quantization": f"{self.quantization_bits}-bit" if self.use_quantization else "None",
            "LoRA adapter": getattr(self.model, 'peft_config', None) or getattr(self.model, 'active_adapter', None) or "None"
        }

        if grouped:
            # Grouped translation: merge lines for each speaker group
            from concurrent.futures import ThreadPoolExecutor
            texts_to_translate = []
            original_texts = []
            all_tags = []
            n_tag_counts = []
            merged_texts = []
            for group in grouped:
                merged_text = ' '.join(group["lines"])
                original_texts.append(merged_text)
                n_count = sum(len(re.findall(r'\\N', t, re.IGNORECASE)) for t in group["lines"])
                n_tag_counts.append(n_count)
                clean_text = re.sub(r'\\N', ' ', merged_text, flags=re.IGNORECASE)
                merged_texts.append(clean_text)
            # Parallel protect_tags
            with ThreadPoolExecutor() as executor:
                tag_results = list(executor.map(self.protect_tags, merged_texts))
            texts_to_translate = [r[0] for r in tag_results]
            all_tags = [r[1] for r in tag_results]

            # Translate
            translated = self.translate(texts_to_translate, src_lang, tgt_lang,
                                       progress_callback=progress_callback)

            # Restore tags and \N
            final_texts = []
            for i, trans in enumerate(translated):
                with_tags = self.restore_tags(trans, all_tags[i])
                with_n = self.insert_n_tags(with_tags, n_tag_counts[i], n_tag_idx)
                final_texts.append(with_n)

            # Rebuild file: distribute translated group text back to original dialogue lines
            output_lines = header[:]
            idx = 0
            for group, trans in zip(grouped, final_texts):
                # Split translated text back into lines (naive split)
                split_trans = trans.split(' ', len(group["lines"]) - 1)
                for j, orig_line in enumerate(group["lines"]):
                    parts = dialogues[idx].split(',', 9)
                    if len(parts) >= 10:
                        parts[9] = split_trans[j] + '\n'
                        output_lines.append(','.join(parts))
                    else:
                        output_lines.append(dialogues[idx])
                    idx += 1

            # Create log file
            duration = time.time() - start_time
            self._write_translation_log(log_path, original_texts, final_texts, setup_info, duration)

            # Save
            with open(out_path, 'w', encoding='utf-8-sig') as f:
                f.writelines(output_lines)

            return out_path, original_texts, final_texts

        else:
            # Fallback: line-by-line translation as before
            from concurrent.futures import ThreadPoolExecutor
            texts_to_translate = []
            original_texts = []
            all_tags = []  # Store tags for each line
            n_tag_counts = []
            clean_texts = []
            for line in dialogues:
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    text = parts[9].rstrip('\n')
                    original_texts.append(text)
                    n_count = len(re.findall(r'\\N', text, re.IGNORECASE))
                    n_tag_counts.append(n_count)
                    clean_text = re.sub(r'\\N', ' ', text, flags=re.IGNORECASE)
                    clean_texts.append(clean_text)
            # Parallel protect_tags
            with ThreadPoolExecutor() as executor:
                tag_results = list(executor.map(self.protect_tags, clean_texts))
            texts_to_translate = [r[0] for r in tag_results]
            all_tags = [r[1] for r in tag_results]

            # Translate
            translated = self.translate(texts_to_translate, src_lang, tgt_lang,
                                       progress_callback=progress_callback)

            # Restore tags and \N
            final_texts = []
            for i, trans in enumerate(translated):
                with_tags = self.restore_tags(trans, all_tags[i])
                with_n = self.insert_n_tags(with_tags, n_tag_counts[i], n_tag_idx)
                final_texts.append(with_n)

            # Create log file
            duration = time.time() - start_time
            self._write_translation_log(log_path, original_texts, final_texts, setup_info, duration)

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
            with open(out_path, 'w', encoding='utf-8-sig') as f:
                f.writelines(output_lines)

            return out_path, original_texts, final_texts
    
    def translate_srt_file(self, input_path: str, src_lang: str, tgt_lang: str,
                           progress_callback=None, preparing_callback=None) -> Tuple[str, List[str], List[str]]:
        """Translate .srt file."""
        import time
        start_time = time.time()
        if preparing_callback:
            preparing_callback("Reading and parsing .srt file... (Preparation time depends on the amount of lines in the file)")
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Split into subtitle blocks
        blocks = re.split(r'\n\s*\n', content.strip())

        texts_to_translate = []
        original_texts = []
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
                protected, _ = self.protect_tags(text)
                texts_to_translate.append(protected)
                block_data.append((index_line, time_line))
        if preparing_callback:
            preparing_callback("Preparing translation batches... (Preparation time depends on the amount of lines in the file)")

        # Translate
        translated = self.translate(texts_to_translate, src_lang, tgt_lang,
                                   progress_callback=progress_callback)

        # Restore tags
        final_texts = []
        all_tags = []
        for i, trans in enumerate(translated):
            _, tags = self.protect_tags(original_texts[i])
            all_tags.append(tags)
            with_tags = self.restore_tags(trans, tags)
            final_texts.append(with_tags)

        # Prepare output/log base paths
        def get_unique_path(base_path, ext):
            path = f"{base_path}{ext}"
            i = 1
            while os.path.exists(path):
                path = f"{base_path}_{i}{ext}"
                i += 1
            return path
        base = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}'
        out_path = get_unique_path(base, '.srt')
        log_path = get_unique_path(base, '_log.txt')

        # Gather setup info
        setup_info = {
            "Model": getattr(self.model, 'name_or_path', str(type(self.model))),
            "Batch size": self.batch_size,
            "Num beams": self.num_beams,
            "Device": self.device,
            "FP16 mode": self.use_fp16,
            "Quantization": f"{self.quantization_bits}-bit" if self.use_quantization else "None",
            "LoRA adapter": getattr(self.model, 'peft_config', None) or getattr(self.model, 'active_adapter', None) or "None"
        }

        # Create log file
        duration = time.time() - start_time
        self._write_translation_log(log_path, original_texts, final_texts, setup_info, duration)

        # Rebuild file
        output_blocks = []
        for i, (idx, time) in enumerate(block_data):
            output_blocks.append(f"{idx}\n{time}\n{final_texts[i]}")

        output_content = '\n\n'.join(output_blocks) + '\n'

        # Save
        with open(out_path, 'w', encoding='utf-8-sig') as f:
            f.write(output_content)

        return out_path, original_texts, final_texts
    
    def translate_txt_file(self, input_path: str, src_lang: str, tgt_lang: str,
                           progress_callback=None, preparing_callback=None) -> Tuple[str, List[str], List[str]]:
        """Translate .txt file."""
        import time
        start_time = time.time()
        if preparing_callback:
            preparing_callback("Reading and parsing .txt file... (Preparation time depends on the amount of lines in the file)")
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
        if preparing_callback:
            preparing_callback("Preparing translation batches... (Preparation time depends on the amount of lines in the file)")

        # Translate
        translated = self.translate(texts_to_translate, src_lang, tgt_lang,
                                   progress_callback=progress_callback)

        # Prepare output/log base paths
        def get_unique_path(base_path, ext):
            path = f"{base_path}{ext}"
            i = 1
            while os.path.exists(path):
                path = f"{base_path}_{i}{ext}"
                i += 1
            return path
        base = input_path.rsplit('.', 1)[0] + f'_{tgt_lang}'
        out_path = get_unique_path(base, '.txt')
        log_path = get_unique_path(base, '_log.txt')

        # Gather setup info
        setup_info = {
            "Model": getattr(self.model, 'name_or_path', str(type(self.model))),
            "Batch size": self.batch_size,
            "Num beams": self.num_beams,
            "Device": self.device,
            "FP16 mode": self.use_fp16,
            "Quantization": f"{self.quantization_bits}-bit" if self.use_quantization else "None",
            "LoRA adapter": getattr(self.model, 'peft_config', None) or getattr(self.model, 'active_adapter', None) or "None"
        }

        # Create log file
        duration = time.time() - start_time
        self._write_translation_log(log_path, original_texts, translated, setup_info, duration)

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
        with open(out_path, 'w', encoding='utf-8-sig') as f:
            f.writelines(output_lines)

        return out_path, original_texts, translated


# ============================================================================
# GUI
# ============================================================================

def run_gui():
    """Run the simplified GUI."""
    
    root = tk.Tk()
    root.title("Subtitle Translator (NLLB)")
    root.geometry("580x440")
    
    # Variables
    file_path = tk.StringVar()
    src_lang = tk.StringVar(value="en")
    tgt_lang = tk.StringVar(value="pl")
    file_type = tk.StringVar(value="ass")
    n_tag_wordidx = tk.IntVar(value=0)
    batch_size_var = tk.IntVar(value=32)  # Increased default from 8 to 32
    num_beams_var = tk.IntVar(value=4)
    use_fp16_var = tk.BooleanVar(value=True)
    use_quantization_var = tk.BooleanVar(value=False)
    quantization_bits_var = tk.StringVar(value="4")
    enable_grouping_var = tk.BooleanVar(value=False)  # Disabled by default for safety
    
    LANG_OPTIONS = ["en", "pl", "ja", "fr", "de"]
    FILE_TYPES = ["ass", "srt", "txt"]
    
    translator = None
    lora_adapter_path = tk.StringVar(value="")
    
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

    # LoRA Adapter Selection
    tk.Label(file_frame, text="LoRA Adapter:").grid(row=1, column=0, sticky="w", padx=2, pady=2)
    tk.Entry(file_frame, textvariable=lora_adapter_path, width=48).grid(row=1, column=1, padx=2, pady=2)

    def browse_adapter():
        dirname = filedialog.askdirectory(title="Select LoRA adapter directory")
        if dirname:
            lora_adapter_path.set(dirname)

    tk.Button(file_frame, text="Browse", command=browse_adapter, width=8).grid(row=1, column=2, padx=2, pady=2)
    
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
    
    # Speaker grouping option (for .ass files with rich speaker names)
    tk.Checkbutton(adv_frame, text="Group by speaker (.ass only)", variable=enable_grouping_var).grid(row=1, column=0, columnspan=3, sticky="w", padx=2, pady=(5,0))

    # Optimization Options Group
    opt_frame = tk.LabelFrame(root, text="Performance Optimizations", padx=5, pady=5)
    opt_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
    tk.Checkbutton(opt_frame, text="FP16 (half precision)", variable=use_fp16_var).grid(row=0, column=0, sticky="w", padx=2)
    tk.Checkbutton(opt_frame, text="Quantization", variable=use_quantization_var).grid(row=0, column=1, sticky="w", padx=2)
    tk.Label(opt_frame, text="Bits:").grid(row=0, column=2, sticky="w", padx=(10,2))
    tk.OptionMenu(opt_frame, quantization_bits_var, "4", "8").grid(row=0, column=3, sticky="w", padx=2)

    # Progress
    progress_label = tk.Label(root, text="Translation: 0%", font=("Arial", 9))
    progress_label.grid(row=4, column=0, columnspan=3, pady=2)

    status_label = tk.Label(root, text="Ready", font=("Arial", 9, "bold"))
    status_label.grid(row=5, column=0, columnspan=3, pady=2)

    start_btn = tk.Button(root, text="Start Translation", width=20, bg="#4CAF50", fg="white")
    start_btn.grid(row=6, column=0, columnspan=3, pady=10)
    

    def update_progress(current, total):
        """Update progress display."""
        if total > 0:
            pct = int((current / total) * 100)
            progress_label.config(text=f"Translation: {pct}%")
            root.update_idletasks()

    def update_preparing(status):
        status_label.config(text=status)
        root.update_idletasks()
    
    def show_review(originals, translations, output_path):
        """Show review window with side-by-side layout, optionally showing speaker names."""
        review_win = tk.Toplevel(root)
        review_win.title("Review Translations")
        review_win.geometry("1300x900")

        # Try to get speaker names using group_dialogues_by_speaker
        # Only works for .ass files, so try to get the file path from output_path
        speaker_names = None
        try:
            if output_path.endswith('.ass'):
                # Try to find the corresponding input file
                input_path = output_path.rsplit('_', 1)[0] + '.ass'
                if os.path.exists(input_path):
                    with open(input_path, 'r', encoding='utf-8-sig') as f:
                        lines = f.readlines()
                    dialogues = [line for line in lines if line.startswith('Dialogue:')]
                    grouped = SubtitleTranslator.group_dialogues_by_speaker(dialogues, enable_grouping=True)
                    if grouped and len(grouped) == len(originals):
                        speaker_names = [g['name'] for g in grouped]
        except Exception:
            speaker_names = None

        # Header frame
        header_frame = tk.Frame(review_win)
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        col = 0
        if speaker_names:
            tk.Label(header_frame, text="Speaker", font=("Arial", 10, "bold"), width=18, anchor="w").grid(row=0, column=col, padx=5)
            col += 1
        tk.Label(header_frame, text="Original", font=("Arial", 10, "bold"), width=50, anchor="w").grid(row=0, column=col, padx=5)
        col += 1
        tk.Label(header_frame, text="Translation", font=("Arial", 10, "bold"), width=70, anchor="w").grid(row=0, column=col, padx=5)

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

        # Populate rows with three-column layout if speaker_names, else two-column
        entry_widgets = []
        for i, (orig, trans) in enumerate(zip(originals, translations)):
            col = 0
            if speaker_names:
                tk.Label(scrollable_frame, text=speaker_names[i], font=("Arial", 9), width=18, anchor="w", bg="#e8e8e8").grid(row=i, column=col, sticky="ew", padx=2, pady=2)
                col += 1
            # Original text (left column)
            orig_text = tk.Text(scrollable_frame, width=50, height=2, wrap=tk.WORD, font=("Arial", 9))
            orig_text.insert("1.0", orig)
            orig_text.config(state="disabled", bg="#f0f0f0")
            orig_text.grid(row=i, column=col, sticky="ew", padx=5, pady=2)
            col += 1
            # Translation (right column - editable)
            trans_entry = tk.Entry(scrollable_frame, width=70, font=("Arial", 9))
            trans_entry.insert(0, trans)
            trans_entry.grid(row=i, column=col, sticky="ew", padx=5, pady=2)
            entry_widgets.append(trans_entry)

        # Configure grid weights for resizing
        for c in range(col+1):
            scrollable_frame.grid_columnconfigure(c, weight=1)

        def save_and_close():
            """Save edited translations and finalize the output file."""
            edited = [e.get() for e in entry_widgets]
            
            # Apply edits to the output file
            try:
                # Re-write the output file with edited translations
                # Read the current file to preserve structure
                with open(output_path, 'r', encoding='utf-8-sig') as f:
                    lines = f.readlines()
                
                # For .ass files, update dialogue lines
                if output_path.endswith('.ass'):
                    dialogue_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith('Dialogue:'):
                            if dialogue_idx < len(edited):
                                parts = line.split(',', 9)
                                if len(parts) >= 10:
                                    parts[9] = edited[dialogue_idx] + '\n'
                                    lines[i] = ','.join(parts)
                                dialogue_idx += 1
                
                # For .srt files, update subtitle text
                elif output_path.endswith('.srt'):
                    trans_idx = 0
                    i = 0
                    while i < len(lines):
                        # Skip index and timestamp lines
                        if lines[i].strip().isdigit():
                            i += 2  # Skip index and timestamp
                            # Now we're at the text - update it
                            if i < len(lines) and trans_idx < len(edited):
                                # Replace all text lines until empty line
                                text_start = i
                                while i < len(lines) and lines[i].strip():
                                    i += 1
                                # Replace the text block with edited version
                                lines[text_start] = edited[trans_idx] + '\n'
                                # Remove extra lines
                                for j in range(text_start + 1, i):
                                    lines[j] = ''
                                trans_idx += 1
                        i += 1
                
                # For .txt files, just replace the lines
                elif output_path.endswith('.txt'):
                    with open(output_path, 'w', encoding='utf-8') as f:
                        for line in edited:
                            f.write(line + '\n')
                
                # Write back the file if not .txt
                if not output_path.endswith('.txt'):
                    with open(output_path, 'w', encoding='utf-8-sig') as f:
                        f.writelines(lines)
                
                # Update the log file with corrected translations
                log_path = output_path.rsplit('.', 1)[0] + '_log.txt'
                if os.path.exists(log_path):
                    try:
                        # Read the existing log file
                        with open(log_path, 'r', encoding='utf-8') as f:
                            log_lines = f.readlines()
                        
                        # Update translations in the log
                        # Format: [Line N]\nOriginal: ...\nTranslation: ...\n
                        trans_idx = 0
                        for i, line in enumerate(log_lines):
                            if line.startswith('Translation:') and trans_idx < len(edited):
                                # Replace the translation line with edited version
                                log_lines[i] = f"Translation: {edited[trans_idx]}\n"
                                trans_idx += 1
                        
                        # Write back the updated log
                        with open(log_path, 'w', encoding='utf-8') as f:
                            f.writelines(log_lines)
                    except Exception as log_err:
                        print(f"Warning: Could not update log file: {log_err}")
                
                review_win.destroy()
                messagebox.showinfo("Success", f"Translation saved!\n\nOutput: {output_path}\nLog file updated with corrections.")
                reset_ui()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save edits:\n{str(e)}")
        
        def cancel_translation():
            """Cancel the translation and delete the output file."""
            try:
                # Delete the output file
                if os.path.exists(output_path):
                    os.remove(output_path)
                # Delete the log file if it exists
                log_path = output_path.rsplit('.', 1)[0] + '_log.txt'
                if os.path.exists(log_path):
                    os.remove(log_path)
                
                review_win.destroy()
                messagebox.showinfo("Cancelled", "Translation cancelled. Output files deleted.")
                reset_ui()
            except Exception as e:
                review_win.destroy()
                messagebox.showerror("Error", f"Failed to clean up files:\n{str(e)}")
                reset_ui()

        # Bottom button frame
        btn_frame = tk.Frame(review_win)
        btn_frame.pack(side=tk.BOTTOM, pady=10)
        tk.Button(btn_frame, text="Approve and Save", command=save_and_close, width=20, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=cancel_translation, width=15, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
    
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
                    lora_path = lora_adapter_path.get().strip() or None
                    translator = SubtitleTranslator(
                        batch_size=batch_size_var.get(),
                        num_beams=num_beams_var.get(),
                        lora_adapter=lora_path,
                        use_fp16=use_fp16_var.get(),
                        use_quantization=use_quantization_var.get(),
                        quantization_bits=int(quantization_bits_var.get())
                    )

                status_label.config(text="Translating...")
                root.update_idletasks()

                # Translate based on file type
                ftype = file_type.get()
                if ftype == "ass":
                    output_path, originals, translations = translator.translate_ass_file(
                        path, src_lang.get(), tgt_lang.get(),
                        n_tag_wordidx.get(), enable_grouping_var.get(),
                        update_progress, update_preparing
                    )
                elif ftype == "srt":
                    output_path, originals, translations = translator.translate_srt_file(
                        path, src_lang.get(), tgt_lang.get(), update_progress, update_preparing
                    )
                else:  # txt
                    output_path, originals, translations = translator.translate_txt_file(
                        path, src_lang.get(), tgt_lang.get(), update_progress, update_preparing
                    )

                status_label.config(text="Complete!")
                progress_label.config(text="Translation: 100%")

                # Show review window
                root.after(0, lambda: show_review(originals, translations, output_path))

            except Exception as e:
                root.after(0, lambda: messagebox.showerror("Error", f"Translation failed:\n{str(e)}"))
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
    # Suppress FutureWarning from huggingface_hub (e.g., resume_download)
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub.file_download")
    """Run CLI mode."""
    parser = argparse.ArgumentParser(description="Subtitle Translator CLI")
    parser.add_argument("input_file", help="Input subtitle file (.ass, .srt, or .txt)")
    parser.add_argument("--src", default="en", help="Source language (default: en)")
    parser.add_argument("--tgt", default="pl", help="Target language (default: pl)")
    parser.add_argument("--nwordix", type=int, default=0, help="Word index for \\N tag insertion (0=auto, .ass only)")
    parser.add_argument("--enable-grouping", action="store_true", help="Enable speaker-based grouping for .ass files with rich speaker names (default: disabled)")
    parser.add_argument("--batch-size", type=int, default=32, help="Initial batch size, adaptive on OOM (default: 32)")
    parser.add_argument("--num-beams", type=int, default=4, help="Beam search width (default: 4)")
    parser.add_argument("--lora-adapter", default=None, help="Path to LoRA adapter directory (optional)")
    parser.add_argument("--fp16", action="store_true", default=True, help="Use FP16 half precision (default: enabled)")
    parser.add_argument("--no-fp16", action="store_false", dest="fp16", help="Disable FP16 half precision")
    parser.add_argument("--quantize", action="store_true", help="Enable quantization (4-bit or 8-bit)")
    parser.add_argument("--quantize-bits", type=int, choices=[4, 8], default=4, help="Quantization bits: 4 or 8 (default: 4)")
    
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
    print(f"Optimizations: FP16={args.fp16}, Quantization={args.quantize}, Batch={args.batch_size}")
    
    # Load translator
    translator = SubtitleTranslator(
        batch_size=args.batch_size, 
        num_beams=args.num_beams, 
        lora_adapter=args.lora_adapter,
        use_fp16=args.fp16,
        use_quantization=args.quantize,
        quantization_bits=args.quantize_bits
    )
    
    def progress_callback(current, total):
        pct = int((current / total) * 100)
        print(f"\rProgress: {current}/{total} ({pct}%)", end='', flush=True)

    def preparing_callback(status):
        print(status)
    
    # Translate
    try:
        if ext == 'ass':
            output_path, _, _ = translator.translate_ass_file(
                args.input_file, args.src, args.tgt,
                args.nwordix, args.enable_grouping,
                progress_callback, preparing_callback
            )
        elif ext == 'srt':
            output_path, _, _ = translator.translate_srt_file(
                args.input_file, args.src, args.tgt, progress_callback, preparing_callback
            )
        else:  # txt
            output_path, _, _ = translator.translate_txt_file(
                args.input_file, args.src, args.tgt, progress_callback, preparing_callback
            )
        
        print(f"\n\nSuccess! Saved to: {output_path}")
        
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Run CLI if any argument is present (file or CLI-style), otherwise run GUI
    if len(sys.argv) > 1:
        run_cli()
    else:
        run_gui()
