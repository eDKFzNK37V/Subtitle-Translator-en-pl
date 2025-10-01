#!/usr/bin/env python3
"""
Batch translation utility for multiple .ass files.
"""

import argparse
import sys
from pathlib import Path
from translate_ass import ASSTranslator


def batch_translate(input_dir: str, output_dir: str, src_lang: str, tgt_lang: str, 
                   pattern: str = "*.ass", model: str = "facebook/nllb-200-3.3B"):
    """
    Batch translate all .ass files in a directory.
    
    Args:
        input_dir: Input directory containing .ass files
        output_dir: Output directory for translated files
        src_lang: Source language code
        tgt_lang: Target language code
        pattern: File pattern to match (default: *.ass)
        model: Model name to use
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist!")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all .ass files
    ass_files = list(input_path.glob(pattern))
    
    if not ass_files:
        print(f"No files matching '{pattern}' found in {input_dir}")
        sys.exit(1)
    
    print(f"Found {len(ass_files)} file(s) to translate")
    
    # Initialize translator once for all files
    translator = ASSTranslator(model_name=model)
    
    # Get language codes
    src_lang_code = translator.LANG_CODES.get(src_lang.lower())
    tgt_lang_code = translator.LANG_CODES.get(tgt_lang.lower())
    
    if not src_lang_code or not tgt_lang_code:
        print(f"Error: Invalid language codes")
        sys.exit(1)
    
    # Translate each file
    for i, input_file in enumerate(ass_files, 1):
        output_file = output_path / input_file.name
        print(f"\n[{i}/{len(ass_files)}] Translating {input_file.name}...")
        
        try:
            translator.translate_ass_file(
                str(input_file),
                str(output_file),
                src_lang_code,
                tgt_lang_code
            )
        except Exception as e:
            print(f"Error translating {input_file.name}: {e}")
            continue
    
    print(f"\nBatch translation complete! Translated files saved to: {output_dir}")


def main():
    """Main function for batch translator."""
    parser = argparse.ArgumentParser(
        description="Batch translate .ass subtitle files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  # Translate all .ass files in a directory
  python batch_translate.py input_dir/ output_dir/ eng fra
        """
    )
    
    parser.add_argument('input_dir', help='Input directory containing .ass files')
    parser.add_argument('output_dir', help='Output directory for translated files')
    parser.add_argument('src_lang', help='Source language code (e.g., eng, jpn)')
    parser.add_argument('tgt_lang', help='Target language code (e.g., eng, fra)')
    parser.add_argument('--pattern', default='*.ass', 
                       help='File pattern to match (default: *.ass)')
    parser.add_argument('--model', default='facebook/nllb-200-3.3B',
                       help='Model name (default: facebook/nllb-200-3.3B)')
    
    args = parser.parse_args()
    
    batch_translate(
        args.input_dir,
        args.output_dir,
        args.src_lang,
        args.tgt_lang,
        args.pattern,
        args.model
    )


if __name__ == "__main__":
    main()
