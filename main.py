# main.py

import sys
import argparse
from gui import run_gui
from subtitle_workflow import translate_with_context_nllb, model_setup
from models import get_nllb_globals, get_m2m100_model
from utils import load_subtitle_lines, save_subtitle_lines


def print_usage():
    print("""
Subtitle Translator Usage:

To use the GUI (recommended for most users):
    python main.py

To translate a subtitle file from the command line:
    python main.py <input_file> [--engine nllb|m2m100] [--src en|pl] [--tgt en|pl]

Examples:
    python main.py example.srt
    python main.py example.srt --engine nllb --src en --tgt pl
    python main.py example.srt --engine m2m100 --src pl --tgt en

If you are not sure, just run: python main.py
""")

print("Any informations about updating any package, can be ignored due to specifics of the app")

def main():
    parser = argparse.ArgumentParser(description="Subtitle Translator CLI", add_help=False)

    parser.add_argument("input_file", nargs="?", help="Subtitle file to translate")
    parser.add_argument("--engine", choices=["nllb", "m2m100"], default="m2m100", help="Translation engine to use (default: m2m100)")
    parser.add_argument("--src", default="en", help="Source language code (default: en)")
    parser.add_argument("--tgt", default="pl", help="Target language code (default: pl)")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message and exit")
    args = parser.parse_args()

    if args.help:
        print_usage()
        return

    if not args.input_file:
        print_usage()
        run_gui()
        return

    # Load model based on engine
    if args.engine == "nllb":
        model, tokenizer, device = get_nllb_globals()
    else:
        model, tokenizer = get_m2m100_model()
        device = "cuda" if hasattr(model, 'to') and hasattr(model, 'device') and model.device.type == "cuda" else "cpu"

    # Load lines
    lines, subs, idx_map = load_subtitle_lines(args.input_file)
    if not lines:
        print("No subtitle lines found.")
        return

    # Translate using the appropriate function based on engine
    if args.engine == "nllb":
        translated = translate_with_context_nllb(
            lines,
            args.src,
            args.tgt,
            model,
            tokenizer,
            device
        )
    else:
        # Use the enhanced translate_batch for M2M100
        from subtitle_workflow import translate_lines
        translated = translate_lines(lines, args.src, args.tgt)
    base, ext = args.input_file.rsplit('.', 1)
    output_path = f"{base}_{args.tgt}.{ext}"
    save_subtitle_lines(translated, output_path, subs, idx_map)
    print(f"Translated file saved to: {output_path}")

if __name__ == "__main__":
    main()
