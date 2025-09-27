# main.py
import argparse
import os
import time
from gui import run_gui
from subtitle_workflow import translate_with_context_nllb, model_setup
from models import get_nllb_globals
from utils import load_subtitle_lines, save_subtitle_lines
from cli_callbacks import on_cli_start, on_cli_progress, on_cli_finish, on_cli_error


def print_usage():
    print("""
Subtitle Translator Usage:

To use the GUI (recommended for most users):
    python main.py

To translate a subtitle file from the command line:
    python main.py <input_file_path> [--src en|pl] [--tgt en|pl]

Examples:
    python main.py example.srt
    python main.py example.srt --src en --tgt pl
    python main.py example.srt --src pl --tgt en

If you are not sure, just run: python main.py
""")

print("Any informations about updating any package, can be ignored due to specifics of the app")

def create_progress_callback(stage_name="translation"):
    """Create a progress callback that reports to CLI callbacks."""
    def progress_callback(current, total):
        on_cli_progress(current, total, stage_name)
    return progress_callback

def main():
    parser = argparse.ArgumentParser(description="Subtitle Translator CLI", add_help=False)

    parser.add_argument("input_file_path", nargs="?", help="Path to the subtitle file to translate")
    parser.add_argument("--src", default="en", help="Source language code (default: en)")
    parser.add_argument("--tgt", default="pl", help="Target language code (default: pl)")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
    args = parser.parse_args()

    if args.help:
        print_usage()
        return

    if not args.input_file_path:
        print_usage()
        run_gui()
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
        # CLI Start event
        on_cli_start(args.input_file_path, args.src, args.tgt, output_path)
        
        # Load NLLB model
        on_cli_progress(1, 4, "initialization")
        model, tokenizer, device = get_nllb_globals()
        
        # Load lines
        on_cli_progress(2, 4, "loading")
        lines, subs, idx_map = load_subtitle_lines(args.input_file_path)
        if not lines:
            on_cli_error("No subtitle lines found in the input file", args.input_file_path)
            return

        # Translate using NLLB with progress callback
        on_cli_progress(3, 4, "translating")
        translated = translate_with_context_nllb(
            lines,
            args.src,
            args.tgt,
            model,
            tokenizer,
            device,
            translation_callback=create_progress_callback("translation")
        )
        
        # Save output
        on_cli_progress(4, 4, "saving")
        save_subtitle_lines(translated, output_path, subs, idx_map)
        
        # Calculate duration and finish
        duration = time.time() - start_time
        on_cli_finish(output_path, len(lines), duration)
        
    except FileNotFoundError as e:
        on_cli_error(f"File not found: {str(e)}", args.input_file_path)
    except PermissionError as e:
        on_cli_error(f"Permission denied: {str(e)}", args.input_file_path)
    except Exception as e:
        on_cli_error(f"Translation failed: {str(e)}", args.input_file_path)

if __name__ == "__main__":
    main()
