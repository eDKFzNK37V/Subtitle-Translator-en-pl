#!/usr/bin/env python3
"""
NLLB Translation App for .ass Subtitle Files

This app translates .ass subtitle files using Facebook's NLLB-3.3B model
while preserving formatting, timestamps, and avoiding translation of tags.
"""

import re
import argparse
import sys
from typing import List, Tuple, Optional
from pathlib import Path

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    from tqdm import tqdm
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)


class ASSTranslator:
    """Translator for .ass subtitle files using NLLB model."""
    
    # NLLB language codes mapping (common ones)
    LANG_CODES = {
        'eng': 'eng_Latn',  # English
        'fra': 'fra_Latn',  # French
        'deu': 'deu_Latn',  # German
        'spa': 'spa_Latn',  # Spanish
        'ita': 'ita_Latn',  # Italian
        'jpn': 'jpn_Jpan',  # Japanese
        'kor': 'kor_Hang',  # Korean
        'zho': 'zho_Hans',  # Chinese (Simplified)
        'rus': 'rus_Cyrl',  # Russian
        'ara': 'arb_Arab',  # Arabic
        'por': 'por_Latn',  # Portuguese
        'nld': 'nld_Latn',  # Dutch
        'pol': 'pol_Latn',  # Polish
        'tur': 'tur_Latn',  # Turkish
        'hin': 'hin_Deva',  # Hindi
        'vie': 'vie_Latn',  # Vietnamese
        'tha': 'tha_Thai',  # Thai
        'ind': 'ind_Latn',  # Indonesian
    }
    
    # Pattern to match .ass tags (everything between {} or with \\)
    TAG_PATTERN = re.compile(r'(\{[^}]*\}|\\[Nn]|\\h)')
    
    def __init__(self, model_name: str = "facebook/nllb-200-3.3B", device: Optional[str] = None):
        """
        Initialize the translator.
        
        Args:
            model_name: HuggingFace model name
            device: Device to use ('cuda' or 'cpu'). Auto-detected if None.
        """
        print(f"Loading model: {model_name}")
        
        # Auto-detect device if not specified
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Using device: {self.device}")
        
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        
        print("Model loaded successfully!")
    
    def parse_ass_file(self, file_path: str) -> Tuple[List[str], List[str]]:
        """
        Parse .ass file and separate header from dialogue lines.
        
        Args:
            file_path: Path to .ass file
            
        Returns:
            Tuple of (header_lines, dialogue_lines)
        """
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        header_lines = []
        dialogue_lines = []
        in_events = False
        
        for line in lines:
            if line.strip().startswith('[Events]'):
                in_events = True
                header_lines.append(line)
            elif in_events and (line.startswith('Dialogue:') or line.startswith('Comment:')):
                dialogue_lines.append(line)
            else:
                header_lines.append(line)
        
        return header_lines, dialogue_lines
    
    def extract_text_from_dialogue(self, dialogue_line: str) -> Tuple[str, str, str]:
        """
        Extract text from dialogue line while preserving format.
        
        Args:
            dialogue_line: A dialogue line from .ass file
            
        Returns:
            Tuple of (prefix, text_to_translate, suffix)
        """
        # Format: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        if not dialogue_line.startswith('Dialogue:'):
            return dialogue_line, "", ""
        
        parts = dialogue_line.split(',', 9)
        if len(parts) < 10:
            return dialogue_line, "", ""
        
        prefix = ','.join(parts[:9]) + ','
        text = parts[9].rstrip('\n')
        
        return prefix, text, '\n'
    
    def protect_tags(self, text: str) -> Tuple[str, List[str]]:
        """
        Replace tags with placeholders to avoid translation.
        
        Args:
            text: Text with tags
            
        Returns:
            Tuple of (text_with_placeholders, list_of_tags)
        """
        tags = []
        
        def replacer(match):
            tags.append(match.group(0))
            return f"<TAG{len(tags)-1}>"
        
        protected_text = self.TAG_PATTERN.sub(replacer, text)
        return protected_text, tags
    
    def restore_tags(self, text: str, tags: List[str]) -> str:
        """
        Restore tags from placeholders.
        
        Args:
            text: Text with placeholders
            tags: List of original tags
            
        Returns:
            Text with restored tags
        """
        for i, tag in enumerate(tags):
            text = text.replace(f"<TAG{i}>", tag)
        return text
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str) -> str:
        """
        Translate text using NLLB model.
        
        Args:
            text: Text to translate
            src_lang: Source language code (e.g., 'eng_Latn')
            tgt_lang: Target language code (e.g., 'fra_Latn')
            
        Returns:
            Translated text
        """
        if not text.strip():
            return text
        
        # Tokenize
        self.tokenizer.src_lang = src_lang
        inputs = self.tokenizer(text, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate translation
        with torch.no_grad():
            translated_tokens = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt_lang],
                max_length=512,
                num_beams=5,
                early_stopping=True
            )
        
        # Decode
        translated_text = self.tokenizer.batch_decode(
            translated_tokens, skip_special_tokens=True
        )[0]
        
        return translated_text
    
    def translate_dialogue_line(self, dialogue_line: str, src_lang: str, tgt_lang: str) -> str:
        """
        Translate a single dialogue line while preserving format and tags.
        
        Args:
            dialogue_line: Dialogue line from .ass file
            src_lang: Source language code
            tgt_lang: Target language code
            
        Returns:
            Translated dialogue line
        """
        prefix, text, suffix = self.extract_text_from_dialogue(dialogue_line)
        
        if not text.strip():
            return dialogue_line
        
        # Protect tags
        protected_text, tags = self.protect_tags(text)
        
        # Translate
        translated_text = self.translate_text(protected_text, src_lang, tgt_lang)
        
        # Restore tags
        final_text = self.restore_tags(translated_text, tags)
        
        return prefix + final_text + suffix
    
    def translate_ass_file(self, input_path: str, output_path: str, 
                          src_lang: str, tgt_lang: str) -> None:
        """
        Translate entire .ass file.
        
        Args:
            input_path: Path to input .ass file
            output_path: Path to output .ass file
            src_lang: Source language code
            tgt_lang: Target language code
        """
        print(f"Translating {input_path}...")
        print(f"Source language: {src_lang}")
        print(f"Target language: {tgt_lang}")
        
        # Parse file
        header_lines, dialogue_lines = self.parse_ass_file(input_path)
        
        # Translate dialogue lines
        translated_dialogues = []
        for dialogue_line in tqdm(dialogue_lines, desc="Translating dialogues"):
            translated_line = self.translate_dialogue_line(dialogue_line, src_lang, tgt_lang)
            translated_dialogues.append(translated_line)
        
        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(header_lines)
            f.writelines(translated_dialogues)
        
        print(f"Translation completed! Output saved to: {output_path}")


def main():
    """Main function to run the translation app."""
    parser = argparse.ArgumentParser(
        description="Translate .ass subtitle files using NLLB-3.3B model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate from English to French
  python translate_ass.py input.ass output.ass eng fra
  
  # Translate from Japanese to English
  python translate_ass.py input.ass output.ass jpn eng
  
Common language codes:
  eng=English, fra=French, deu=German, spa=Spanish, ita=Italian,
  jpn=Japanese, kor=Korean, zho=Chinese, rus=Russian, ara=Arabic,
  por=Portuguese, nld=Dutch, pol=Polish, tur=Turkish, hin=Hindi,
  vie=Vietnamese, tha=Thai, ind=Indonesian
        """
    )
    
    parser.add_argument('input', help='Input .ass file path')
    parser.add_argument('output', help='Output .ass file path')
    parser.add_argument('src_lang', help='Source language code (e.g., eng, jpn, fra)')
    parser.add_argument('tgt_lang', help='Target language code (e.g., eng, fra, spa)')
    parser.add_argument('--model', default='facebook/nllb-200-3.3B',
                       help='Model name (default: facebook/nllb-200-3.3B)')
    parser.add_argument('--device', choices=['cuda', 'cpu'], default=None,
                       help='Device to use (default: auto-detect)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.input).exists():
        print(f"Error: Input file '{args.input}' not found!")
        sys.exit(1)
    
    # Convert language codes to NLLB format
    translator = ASSTranslator(model_name=args.model, device=args.device)
    
    src_lang_code = translator.LANG_CODES.get(args.src_lang.lower())
    tgt_lang_code = translator.LANG_CODES.get(args.tgt_lang.lower())
    
    if not src_lang_code:
        print(f"Error: Unknown source language code '{args.src_lang}'")
        print(f"Available codes: {', '.join(translator.LANG_CODES.keys())}")
        sys.exit(1)
    
    if not tgt_lang_code:
        print(f"Error: Unknown target language code '{args.tgt_lang}'")
        print(f"Available codes: {', '.join(translator.LANG_CODES.keys())}")
        sys.exit(1)
    
    # Translate
    translator.translate_ass_file(
        args.input,
        args.output,
        src_lang_code,
        tgt_lang_code
    )


if __name__ == "__main__":
    main()
