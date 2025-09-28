# main.py
import argparse
import os
import time
from logs import on_cli_start, on_cli_progress, on_cli_finish, on_cli_error, SubtitleLogger


def print_usage():
    print("""
Subtitle Translator Usage:

To use the GUI (recommended for most users):
    python main.py

To translate a subtitle file from the command line:
    python main.py <input_file_path> [--src en|pl] [--tgt en|pl] [--nwordix N]

Examples:
    python main.py example.ass
    python main.py example.ass --src en --tgt pl
    python main.py example.ass --src pl --tgt en
    python main.py example.ass --nwordix 'count of words needed for \\N'
If you are not sure, just run: python main.py
""")

print("Any informations about updating any package, can be ignored due to specifics of the app")

def create_translation_callback(stage_name="translation"):
    """Create a translation progress callback."""
    def callback(current, total):
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"\r{stage_name.capitalize()}: {current}/{total} ({percentage:.0f}%)", end='', flush=True)
        if current >= total:
            print()  # New line when complete
    return callback

def create_post_processing_callback():
    """Create a post-processing progress callback."""
    def callback(current, total):
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"\rPost-processing: {current}/{total} ({percentage:.0f}%)", end='', flush=True)
        if current >= total:
            print()  # New line when complete
    return callback

def main():
    parser = argparse.ArgumentParser(description="Subtitle Translator CLI", add_help=False)

    parser.add_argument("input_file_path", nargs="?", help="Path to the subtitle file to translate")
    parser.add_argument("--src", default="en", help="Source language code (default: en)")
    parser.add_argument("--tgt", default="pl", help="Target language code (default: pl)")
    parser.add_argument("--nwordix", default=0, type=int, help="Word index after which word to insert \\N tags (default: 0, context-aware if 0)")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
    args = parser.parse_args()

    if args.help:
        print_usage()
        return

    if not args.input_file_path:
        print_usage()
        # Import GUI only when needed
        try:
            from gui import run_gui
            run_gui()
        except ImportError as e:
            print(f"GUI not available: {e}")
            print("Please install required dependencies or use CLI mode with a file argument.")
        return

    # Validate input file exists
    if not os.path.exists(args.input_file_path):
        on_cli_error(f"Input file not found: {args.input_file_path}", args.input_file_path)
        return

    start_time = time.time()
    
    # Prepare output path
    base, ext = args.input_file_path.rsplit('.', 1)
    output_path = f"{base}_{args.tgt}.{ext}"
    
    try:
        # Import translation modules only when needed
        from subtitle_workflow import translate_with_context_nllb, correct_text_batch_nllb
        from models import get_nllb_globals
        from utils import load_subtitle_lines, save_subtitle_lines
        from text_tools import (
            extract_newline_tags, insert_newline_tags_at_wordidx, 
            extract_tags_with_placeholders, restore_tags_from_placeholders,
            group_dialogue_lines, split_grouped_translations,
            insert_newline_tags_contextaware
        )
        
        # CLI Start event
        on_cli_start(args.input_file_path, args.src, args.tgt, output_path)
        
        # Load NLLB model
        print("Initialization: Loading NLLB model...")
        model, tokenizer, device = get_nllb_globals()
        
        # Load subtitle lines
        print("Loading subtitle file...")
        texts, subs, idx_map = load_subtitle_lines(args.input_file_path)
        if not texts:
            on_cli_error("No subtitle lines found in the input file", args.input_file_path)
            return

        # Extract \N tags before translation (same as GUI)
        cleaned_lines = []
        n_tag_counts = []
        for line in texts:
            cleaned, n_count = extract_newline_tags(line)
            cleaned_lines.append(cleaned)
            n_tag_counts.append(n_count)
        
        # Extract placeholder tags from cleaned lines (same as GUI)
        placeholder_maps = [extract_tags_with_placeholders(line)[1] for line in cleaned_lines]
        
        # Group dialogue lines for translation (same as GUI)
        grouped_lines, group_map = group_dialogue_lines(cleaned_lines)
        
        # Store originals for logging
        originals = cleaned_lines[:]
        
        # Translation phase
        print(f"Translating {len(grouped_lines)} grouped lines...")
        translated_groups = translate_with_context_nllb(
            grouped_lines,
            args.src,
            args.tgt,
            model,
            tokenizer,
            device,
            translation_callback=create_translation_callback("translation")
        )
        
        # Split translations back to original lines (same as GUI)
        translated = split_grouped_translations(translated_groups, group_map)
        
        # Save intermediate translation (same as GUI)
        save_subtitle_lines(translated, output_path, subs, idx_map)
        
        # Post-processing phase (missing from original CLI!)
        print(f"Post-processing {len(translated)} lines...")
        
        # Create logger (same as GUI)
        logger = SubtitleLogger(args.input_file_path, args.tgt, idx_map=idx_map)
        
        # Correct text using NLLB correction (same as GUI)
        corrected_all = correct_text_batch_nllb(
            translated,
            args.src,
            args.tgt,
            translation_callback=create_post_processing_callback()
        )
        
        # Restore placeholder tags after post-processing (same as GUI)
        restored_placeholders = [
            restore_tags_from_placeholders(corrected_all[i], placeholder_maps[i])
            for i in range(len(corrected_all))
        ]
        
        # Re-insert \N tags at word index 0 (same as GUI default)
        n_wordidx = args.nwordix
        final_lines = []
        for line, n_count, orig in zip(restored_placeholders, n_tag_counts, originals):
            if n_count > 0:
                if n_wordidx == 0:
                    # Use context-aware placement (like GUI)
                    final_lines.append(insert_newline_tags_contextaware(line, n_count, prefer_punctuation=True))
                else:
                    final_lines.append(insert_newline_tags_at_wordidx(line, n_count, n_wordidx))
            else:
                final_lines.append(line)
        
        # Log all entries (same as GUI)
        for idx, (orig, trans, restored, final) in enumerate(zip(originals, translated, restored_placeholders, final_lines)):
            try:
                logger.log_entry(idx, orig, trans, final, tags_before=[], tags_after=[])
            except Exception as e:
                print(f"Warning: Logging failed on line {idx+1}: {e}")
        
        # Write log summary
        try:
            logger.write_summary()
            log_path = logger.get_log_path() if hasattr(logger, "get_log_path") else logger.log_txt
        except Exception as e:
            print(f"Warning: Failed writing log summary: {e}")
            log_path = None
        
        # Save final output with post-processing and \N tags
        save_subtitle_lines(final_lines, output_path, subs, idx_map)
        
        # Calculate duration and finish
        duration = time.time() - start_time
        on_cli_finish(output_path, len(texts), duration)
        
        # Show log path like GUI does
        if log_path and os.path.exists(log_path):
            print(f"Log saved to: {log_path}")
        
    except ImportError as e:
        on_cli_error(f"Missing dependencies: {str(e)}", args.input_file_path)
        print("Please install required dependencies from requirements.txt")
    except FileNotFoundError as e:
        on_cli_error(f"File not found: {str(e)}", args.input_file_path)
    except PermissionError as e:
        on_cli_error(f"Permission denied: {str(e)}", args.input_file_path)
    except Exception as e:
        on_cli_error(f"Translation failed: {str(e)}", args.input_file_path)

if __name__ == "__main__":
    main()
