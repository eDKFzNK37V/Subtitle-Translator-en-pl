"""
Simplified logging module for subtitle translation.
Provides basic logging functionality without excessive complexity.
"""

import os
from datetime import datetime
from typing import Optional


class SubtitleLogger:
    """Simple logger for subtitle translation sessions."""
    
    def __init__(self, file_path: str, lang: str):
        """Initialize logger with file path and target language."""
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        log_dir = os.path.dirname(file_path) or '.'
        self.log_txt = os.path.join(log_dir, f"{base_name}_log_{timestamp}.txt")
        
        self.lang = lang
        self.total_changes = 0
        self.entries = []
        
        self._write_header()
    
    def _write_header(self):
        """Write log file header."""
        with open(self.log_txt, "w", encoding="utf-8") as f:
            f.write(f"Subtitle Translation Log\n")
            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Target Language: {self.lang}\n")
            f.write("=" * 60 + "\n\n")
    
    def log_entry(self, index: int, original: str, translated: str, corrected: str,
                  tags_before: list, tags_after: list):
        """Log a single translation entry."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.total_changes += 1
        
        # Write to file
        with open(self.log_txt, "a", encoding="utf-8") as f:
            f.write(f"[Line {index + 1}] — {timestamp}\n")
            f.write(f"Original:   {original}\n")
            f.write(f"Translated: {translated}\n")
            f.write(f"Corrected:  {corrected}\n")
            if tags_before != tags_after:
                f.write(f"Tags changed:\n")
                f.write(f"  Before: {tags_before}\n")
                f.write(f"  After:  {tags_after}\n")
            f.write("-" * 60 + "\n")
        
        # Also print to console
        print(f"[Line {index + 1}] — {timestamp}")
        print(f"Original:   {original}")
        print(f"Translated: {translated}")
        print(f"Corrected:  {corrected}")
        if tags_before != tags_after:
            print(f"Tags changed:")
            print(f"  Before: {tags_before}")
            print(f"  After:  {tags_after}")
        print("-" * 60)
    
    def write_summary(self):
        """Write summary to log file."""
        with open(self.log_txt, "a", encoding="utf-8") as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"Translation Summary\n")
            f.write(f"Total lines processed: {self.total_changes}\n")
            f.write(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


# Simple session tracking
_session_data = {
    'corrections': [],
    'log_path': None
}


def accumulate_correction_data(original_lines: list, corrected_lines: list) -> None:
    """Accumulate correction data for session logging."""
    global _session_data
    for orig, corr in zip(original_lines, corrected_lines):
        if orig != corr:
            _session_data['corrections'].append({
                'original': orig,
                'corrected': corr
            })


def initialize_session_log(output_dir=None):
    """Initialize session logging directory."""
    global _session_data
    if output_dir is None:
        output_dir = '.'
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(output_dir, f"session_{timestamp}.log")
    _session_data['log_path'] = log_path
    _session_data['corrections'] = []


def write_session_log() -> None:
    """Write accumulated session data to log file."""
    global _session_data
    
    if not _session_data['log_path']:
        return
    
    with open(_session_data['log_path'], 'w', encoding='utf-8') as f:
        f.write(f"Session Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total corrections: {len(_session_data['corrections'])}\n")
        f.write("=" * 60 + "\n\n")
        
        for i, corr in enumerate(_session_data['corrections'], 1):
            f.write(f"[{i}]\n")
            f.write(f"Original:  {corr['original']}\n")
            f.write(f"Corrected: {corr['corrected']}\n")
            f.write("-" * 60 + "\n")


def log_names_and_unknown_words(original_lines: list, corrected_lines: list, 
                                  log_file: str = "correction_log.txt") -> None:
    """Log potential names and unknown words (simplified version)."""
    import re
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Correction Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        for i, (orig, corr) in enumerate(zip(original_lines, corrected_lines), 1):
            if orig != corr:
                # Find capitalized words (potential names)
                orig_caps = set(re.findall(r'\b[A-Z][a-z]+\b', orig))
                corr_caps = set(re.findall(r'\b[A-Z][a-z]+\b', corr))
                
                if orig_caps != corr_caps:
                    f.write(f"[Line {i}] Name changes detected:\n")
                    f.write(f"  Original: {orig}\n")
                    f.write(f"  Corrected: {corr}\n")
                    f.write(f"  Names in original: {', '.join(orig_caps)}\n")
                    f.write(f"  Names in corrected: {', '.join(corr_caps)}\n")
                    f.write("-" * 60 + "\n")


# Simple CLI event logging
def on_cli_start(input_file: str, src_lang: str, tgt_lang: str, output_file: Optional[str] = None):
    """Log CLI translation start."""
    print(f"\nStarting translation: {input_file}")
    print(f"Languages: {src_lang} -> {tgt_lang}")


def on_cli_progress(current: int, total: int, stage: str = "processing"):
    """Log CLI progress."""
    percentage = (current / total * 100) if total > 0 else 0
    print(f"\r{stage}: {current}/{total} ({percentage:.0f}%)", end='', flush=True)


def on_cli_finish(output_file: str, total_lines: int, duration: Optional[float] = None):
    """Log CLI translation completion."""
    print(f"\n\nTranslation complete!")
    print(f"Output: {output_file}")
    print(f"Processed {total_lines} lines")
    if duration:
        print(f"Duration: {duration:.1f}s")


def on_cli_error(error_msg: str, input_file: Optional[str] = None):
    """Log CLI error."""
    print(f"\nError: {error_msg}")
    if input_file:
        print(f"File: {input_file}")
