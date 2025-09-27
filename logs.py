
import os
import re
from datetime import datetime
from typing import Optional, Callable, Dict, Any


# CLI Callback Classes and Functions (moved from cli_callbacks.py)
class CLIEventData:
    """Data structure for CLI events containing relevant information."""
    
    def __init__(self, event_type: str, input_file: str = None, output_file: str = None, 
                 src_lang: str = None, tgt_lang: str = None, status: str = None, 
                 error_msg: str = None, progress: tuple = None, log_path: str = None, 
                 timestamp: datetime = None):
        self.event_type = event_type
        self.input_file = input_file
        self.output_file = output_file
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.status = status
        self.error_msg = error_msg
        self.progress = progress  # (current, total)
        self.log_path = log_path
        self.timestamp = timestamp or datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert event data to dictionary for logging."""
        return {
            'event_type': self.event_type,
            'input_file': self.input_file,
            'output_file': self.output_file,
            'src_lang': self.src_lang,
            'tgt_lang': self.tgt_lang,
            'status': self.status,
            'error_msg': self.error_msg,
            'progress': self.progress,
            'log_path': self.log_path,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class CLICallbackManager:
    """
    Manages CLI callbacks and event logging.
    Provides centralized callback registration and event dispatch.
    """
    
    def __init__(self):
        self.callbacks = {
            'on_start': [],
            'on_progress': [],
            'on_finish': [],
            'on_error': []
        }
        self.session_data = {
            'start_time': None,
            'end_time': None,
            'input_file': None,
            'output_file': None,
            'src_lang': None,
            'tgt_lang': None,
            'total_lines': 0,
            'errors': [],
            'events': []
        }
        self.logger: Optional['SubtitleLogger'] = None
        
    def register_callback(self, event_type: str, callback: Callable[[CLIEventData], None]):
        """Register a callback for a specific event type."""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            raise ValueError(f"Unknown event type: {event_type}")
    
    def _dispatch_event(self, event_data: CLIEventData):
        """Dispatch event to all registered callbacks and log the event."""
        # Store event in session data
        self.session_data['events'].append(event_data.to_dict())
        
        # Update session data based on event type
        if event_data.event_type == 'start':
            self.session_data['start_time'] = event_data.timestamp
            self.session_data['input_file'] = event_data.input_file
            self.session_data['src_lang'] = event_data.src_lang
            self.session_data['tgt_lang'] = event_data.tgt_lang
        elif event_data.event_type == 'finish':
            self.session_data['end_time'] = event_data.timestamp
            self.session_data['output_file'] = event_data.output_file
        elif event_data.event_type == 'error':
            self.session_data['errors'].append(event_data.error_msg)
        
        # Dispatch to registered callbacks
        event_callbacks = self.callbacks.get(f'on_{event_data.event_type}', [])
        for callback in event_callbacks:
            try:
                callback(event_data)
            except Exception as e:
                print(f"Warning: Callback error for {event_data.event_type}: {e}")
    
    def on_start(self, input_file: str, src_lang: str, tgt_lang: str, output_file: str = None):
        """Called when CLI translation starts."""
        # Initialize session logging
        if output_file:
            output_dir = os.path.dirname(output_file)
            initialize_session_log(output_dir)
        else:
            initialize_session_log()
        
        # Create subtitle logger if we have file info
        if input_file and tgt_lang:
            try:
                self.logger = SubtitleLogger(input_file, tgt_lang)
            except Exception as e:
                print(f"Warning: Could not create subtitle logger: {e}")
        
        event_data = CLIEventData(
            event_type='start',
            input_file=input_file,
            output_file=output_file,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            status='started'
        )
        self._dispatch_event(event_data)
        
        # Console output
        print(f"Starting translation: {os.path.basename(input_file)} ({src_lang} → {tgt_lang})")
        if output_file:
            print(f"Output will be saved to: {os.path.basename(output_file)}")
    
    def on_progress(self, current: int, total: int, stage: str = "processing"):
        """Called during translation progress."""
        event_data = CLIEventData(
            event_type='progress',
            progress=(current, total),
            status=f"{stage}: {current}/{total}"
        )
        self._dispatch_event(event_data)
        
        # Console progress update
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"\r{stage.capitalize()}: {current}/{total} ({percentage:.1f}%)", end='', flush=True)
        
        if current >= total:
            print()  # New line when complete
    
    def on_finish(self, output_file: str, total_lines: int, duration: float = None):
        """Called when CLI translation finishes successfully."""
        # Write session logs
        write_session_log()
        
        # Finalize subtitle logger if available
        if self.logger:
            try:
                self.logger.write_summary()
                log_path = self.logger.get_log_path()
            except Exception as e:
                print(f"Warning: Could not write subtitle log: {e}")
                log_path = None
        else:
            log_path = None
        
        event_data = CLIEventData(
            event_type='finish',
            output_file=output_file,
            status='completed',
            log_path=log_path
        )
        self._dispatch_event(event_data)
        
        # Console output
        print(f"✓ Translation completed successfully!")
        print(f"Output saved to: {output_file}")
        if total_lines > 0:
            print(f"Processed {total_lines} lines")
        if duration:
            print(f"Duration: {duration:.1f}s")
        if log_path and os.path.exists(log_path):
            print(f"Log saved to: {log_path}")
    
    def on_error(self, error_msg: str, input_file: str = None):
        """Called when CLI translation encounters an error."""
        event_data = CLIEventData(
            event_type='error',
            input_file=input_file,
            status='failed',
            error_msg=error_msg
        )
        self._dispatch_event(event_data)
        
        # Console output
        print(f"✗ Translation failed: {error_msg}")
        
        # Still try to write session logs in case of error
        try:
            write_session_log()
        except Exception:
            pass
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of the current CLI session."""
        duration = None
        if self.session_data['start_time'] and self.session_data['end_time']:
            duration = (self.session_data['end_time'] - self.session_data['start_time']).total_seconds()
        
        return {
            'input_file': self.session_data['input_file'],
            'output_file': self.session_data['output_file'],
            'src_lang': self.session_data['src_lang'],
            'tgt_lang': self.session_data['tgt_lang'],
            'duration': duration,
            'total_events': len(self.session_data['events']),
            'errors': len(self.session_data['errors']),
            'success': len(self.session_data['errors']) == 0
        }


class SubtitleLogger:
    def __init__(self, file_path, target_lang, idx_map=None):
        self.file_path = file_path
        self.target_lang = target_lang
        self.idx_map = idx_map or []
        self.entries = []
        self.cli_events = []  # Store CLI events
        self.log_txt = self._make_log_path(file_path)

    def _make_log_path(self, file_path):
        base, _ = os.path.splitext(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base}_log_{timestamp}.txt"

    def log_cli_event(self, event_type, details=None):
        """Log CLI events (start, progress, finish, error) for comprehensive tracking."""
        cli_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details or {}
        }
        self.cli_events.append(cli_event)

    def log_entry(self, idx, original, translated, corrected, tags_before=None, tags_after=None):
        """
        Record a single translation/correction entry.
        idx: index in the processed list (not the original file index)
        """
        source_index = self.idx_map[idx] if idx < len(self.idx_map) else None
        self.entries.append({
            "source_index": source_index,
            "original": original,
            "translated": translated,
            "corrected": corrected,
            "tags_before": tags_before or [],
            "tags_after": tags_after or []
        })

    def write_summary(self):
        """
        Write all logged entries to the log file in a human-readable format.
        Includes CLI events if available.
        """
        with open(self.log_txt, "w", encoding="utf-8-sig") as f:
            f.write(f"Log for: {self.file_path}\n")
            f.write(f"Target language: {self.target_lang}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")

            # Write CLI events if any
            if self.cli_events:
                f.write("CLI EVENTS:\n")
                f.write("-" * 30 + "\n")
                for event in self.cli_events:
                    f.write(f"[{event['timestamp']}] {event['event_type'].upper()}\n")
                    if event['details']:
                        for key, value in event['details'].items():
                            f.write(f"  {key}: {value}\n")
                    f.write("\n")
                f.write("\n")

            # Write translation entries
            if self.entries:
                f.write("TRANSLATION ENTRIES:\n")
                f.write("-" * 30 + "\n")
                for entry in self.entries:
                    idx_str = (
                        f"[Source index: {entry['source_index']}]"
                        if entry["source_index"] is not None
                        else "[Source index: ?]"
                    )
                    f.write(f"{idx_str}\n")
                    f.write(f"Original: {entry['original']}\n")
                    f.write(f"Translated: {entry['translated']}\n")
                    f.write(f"Corrected: {entry['corrected']}\n")
                    if entry["tags_before"] or entry["tags_after"]:
                        f.write(f"Tags before: {entry['tags_before']}\n")
                        f.write(f"Tags after: {entry['tags_after']}\n")
                    f.write("\n")

    def get_log_path(self):
        return self.log_txt


# Global storage for session-wide correction logging
_session_log_data = {
    'detected_names': set(),
    'unknown_words': set(),
    'problematic_changes': [],
    'session_started': False,
    'log_file': None
}
# Utility to get next available correction log filename in a directory
def get_next_correction_log_path(output_dir):
    """
    Returns the next available correction log file path in the output directory.
    Pattern: correction_log.txt, correction_log(1).txt, correction_log(2).txt, ...
    """
    base_name = "correction_log.txt"
    log_path = os.path.join(output_dir, base_name)
    if not os.path.exists(log_path):
        return log_path
    n = 1
    while True:
        log_path = os.path.join(output_dir, f"correction_log({n}).txt")
        if not os.path.exists(log_path):
            return log_path
        n += 1

def initialize_session_log(output_dir=None):
    """Initialize a single log file for the entire translation session in the output directory."""
    global _session_log_data
    if not _session_log_data['session_started']:
        if output_dir is not None:
            _session_log_data['log_file'] = get_next_correction_log_path(output_dir)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            _session_log_data['log_file'] = f"correction_log_{timestamp}.txt"
        _session_log_data['session_started'] = True
        _session_log_data['detected_names'] = set()
        _session_log_data['unknown_words'] = set()
        _session_log_data['problematic_changes'] = []


def is_likely_unknown_word(word: str) -> bool:
    """Check if a word is likely unknown/foreign and should be logged."""
    # Skip very short words or non-alphabetic words
    if len(word) < 3 or not word.isalpha():
        return False
        
    # Extended list of common English words to exclude
    common_english = {
        'the', 'and', 'but', 'for', 'you', 'are', 'its', 'it\'s', 'don\'t', 'can\'t', 'won\'t',
        'hello', 'hi', 'yes', 'no', 'this', 'that', 'with', 'have', 'will', 'would', 'could',
        'should', 'there', 'here', 'where', 'when', 'what', 'why', 'how', 'who', 'which',
        'time', 'good', 'bad', 'big', 'small', 'new', 'old', 'first', 'last', 'long', 'short',
        'right', 'left', 'high', 'low', 'hot', 'cold', 'know', 'think', 'make', 'take', 'come',
        'give', 'look', 'use', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave',
        'want', 'need', 'get', 'going', 'said', 'like', 'just', 'really', 'actually', 'maybe',
        'something', 'nothing', 'everything', 'anything', 'someone', 'everyone', 'anyone',
        'about', 'after', 'before', 'during', 'while', 'until', 'since', 'from', 'into', 'onto',
        'off', 'out', 'over', 'under', 'through', 'around', 'between', 'among', 'against', 'along',
        'sword', 'skill', 'power', 'magic', 'weapon', 'shield', 'armor', 'battle', 'fight',
        'attack', 'defend', 'player', 'great', 'strong', 'weak', 'help', 'visit', 'today',
        'uses', 'powerful', 'funny', 'everyone', 'blue', 'red', 'green', 'white', 'black'
    }
    
    if word.lower() in common_english:
        return False
        
    # Extended list of common Polish words to exclude  
    common_polish = {
        'będę', 'dziś', 'jest', 'mam', 'czy', 'ale', 'tak', 'nie', 'co', 'jak', 'gdzie', 
        'kiedy', 'dlaczego', 'który', 'która', 'które', 'tego', 'tej', 'tym', 'tych',
        'jego', 'jej', 'ich', 'nasz', 'nasza', 'nasze', 'wasz', 'wasza', 'wasze',
        'bardzo', 'dobrze', 'źle', 'może', 'tylko', 'już', 'jeszcze', 'także',
        'też', 'również', 'jednak', 'więc', 'przez', 'przed', 'po', 'podczas', 'bez',
        'ciągle', 'zawsze', 'nigdy', 'czasami', 'często', 'rzadko', 'wcześnie', 'późno',
        'tutaj', 'tam', 'wszędzie', 'nigdzie', 'gdzieś', 'daleko', 'blisko', 'obok',
        'chce', 'chcę', 'chcesz', 'chcemy', 'chcecie', 'chcą', 'może', 'musi', 'musisz'
    }
    
    if word.lower() in common_polish:
        return False
    
    # Game/Anime character names and terms that should be flagged for review
    known_names = {
        'kirito', 'asuna', 'argo', 'lind', 'kibaou', 'diabel', 'aincrad', 'karluin',
        'klein', 'silica', 'leafa', 'sinon', 'yui', 'lizbeth', 'agil', 'heathcliff',
        'aincrad', 'alfheim', 'ggo', 'underworld', 'sao', 'alo', 'sword', 'online',
        'gleam', 'eyes', 'excalibur', 'elucidator', 'blue', 'rose', 'beater'
    }
    
    if word.lower() in known_names:
        return True
        
    # Consider words with non-standard patterns as potentially unknown
    unusual_patterns = [
        r'^[A-Z]{3,}$',  # All caps words (acronyms, etc.)
        r'^[A-Z][a-z]*[A-Z]',  # CamelCase  
        r'[xzqj]{2,}',  # Unusual letter combinations
        r'[0-9]',  # Words containing numbers
    ]
    
    for pattern in unusual_patterns:
        if re.search(pattern, word):
            return True
    
    # Check for Polish diacritics - these are important
    polish_chars = 'ąćęłńóśźż'
    if any(char in word.lower() for char in polish_chars):
        return True
            
    # Consider capitalized words that are likely proper names (Japanese names, foreign names)
    # Exclude common English capitalized words
    excluded_caps = {
        'Hello', 'Good', 'Yes', 'No', 'Please', 'Thank', 'Thanks', 'Sorry', 'Okay', 'Ok',
        'Maybe', 'Really', 'Sure', 'Fine', 'Great', 'Well', 'Right', 'Left', 'Up', 'Down',
        'Boss', 'Floor', 'Squad', 'Team', 'Guild', 'Leader', 'Room', 'Raid', 'Attack',
        'Game', 'Player', 'Level', 'Item', 'Skill', 'Magic', 'Sword', 'Shield', 'Armor',
        'Health', 'Status', 'Menu', 'Settings', 'World', 'Area', 'Zone', 'Map', 'Quest'
    }
    
    if word in excluded_caps:
        return False
        
    # Names are typically capitalized and longer than 3 chars
    if word[0].isupper() and len(word) > 3:
        # Additional check: Japanese-style names or obviously foreign names
        japanese_patterns = ['ki', 'to', 'na', 'su', 'ra', 'yu', 'ba', 'go', 'rin', 'ka', 'mi']
        if any(pattern in word.lower() for pattern in japanese_patterns):
            return True
        # Or names that don't look like common English words
        if not re.match(r'^[A-Z][a-z]+$', word):
            return True
        # Long capitalized words that might be names
        if len(word) > 6:
            return True
            
    return False


def accumulate_correction_data(original_lines: list, corrected_lines: list) -> None:
    """
    Accumulate data about corrections for later logging.
    Focus on unknown words (names, titles, etc.) that were translated from English.
    """
    global _session_log_data
    
    initialize_session_log()
    
    for i, (original, corrected) in enumerate(zip(original_lines, corrected_lines)):
        if original == corrected:
            continue
            
        # Detect potential names and unknown words
        original_words = set(re.findall(r'\b\w+\b', original))
        corrected_words = set(re.findall(r'\b\w+\b', corrected))
        
        # Check for lost words that might be names or unknown words
        lost_words = original_words - corrected_words
        for word in lost_words:
            if is_likely_unknown_word(word):
                _session_log_data['unknown_words'].add(word)
                
                # Track significant changes
                _session_log_data['problematic_changes'].append({
                    'original': original,
                    'corrected': corrected,
                    'lost_word': word
                })
        
        # Also check for new words that appeared during correction (might be mistranslations)
        # But only for English words that seem out of place in Polish text
        new_words = corrected_words - original_words
        for word in new_words:
            # Only flag English words that appear in Polish translations (likely mistakes)
            if (is_likely_unknown_word(word) and len(word) > 4 and 
                not any(char in word.lower() for char in 'ąćęłńóśźż') and  # Not Polish word
                word.lower() not in {'dziś', 'miecza', 'gracz', 'pomaga', 'wszystkim', 'potężna', 'używa', 'wspaniały', 'zabawny', 'jest'}):
                # Only flag significant new words that might be incorrect
                _session_log_data['problematic_changes'].append({
                    'original': original,
                    'corrected': corrected,
                    'new_word': word
                })


def write_session_log() -> None:
    """Write the accumulated session data to a single log file."""
    global _session_log_data
    
    if not _session_log_data['session_started'] or not _session_log_data['log_file']:
        return
    
    # Don't write empty logs
    if not (_session_log_data['unknown_words'] or _session_log_data['problematic_changes']):
        return
    
    try:
        with open(_session_log_data['log_file'], 'w', encoding='utf-8') as f:
            f.write("=== CORRECTION SESSION ANALYSIS ===\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            
            if _session_log_data['unknown_words']:
                f.write("UNKNOWN/FOREIGN WORDS DETECTED:\n")
                f.write("(Review these - they may be proper names, titles, or important terms)\n\n")
                for word in sorted(_session_log_data['unknown_words']):
                    f.write(f"- {word}\n")
                f.write("\n")
            
            if _session_log_data['problematic_changes']:
                f.write("PROBLEMATIC CHANGES:\n")
                f.write("(Corrections that may have affected important words)\n\n")
                
                # Group similar changes to reduce noise
                lost_word_groups = {}
                new_word_groups = {}
                
                for change in _session_log_data['problematic_changes']:
                    if 'lost_word' in change:
                        key = change['lost_word']
                        if key not in lost_word_groups:
                            lost_word_groups[key] = []
                        lost_word_groups[key].append(change)
                    elif 'new_word' in change:
                        key = change['new_word']
                        if key not in new_word_groups:
                            new_word_groups[key] = []
                        new_word_groups[key].append(change)
                
                if lost_word_groups:
                    f.write("LOST WORDS (possibly important names/terms):\n")
                    for word, changes in sorted(lost_word_groups.items()):
                        f.write(f"\nLost word: '{word}' ({len(changes)} occurrences)\n")
                        # Show only first few examples to avoid spam
                        for change in changes[:2]:
                            f.write(f"  Original:  {change['original']}\n")
                            f.write(f"  Corrected: {change['corrected']}\n")
                        if len(changes) > 2:
                            f.write(f"  ... and {len(changes) - 2} more occurrences\n")
                    f.write("\n")
                
                if new_word_groups:
                    f.write("NEW WORDS (possibly mistranslations):\n")
                    for word, changes in sorted(new_word_groups.items()):
                        f.write(f"\nNew word: '{word}' ({len(changes)} occurrences)\n")
                        # Show only first few examples to avoid spam
                        for change in changes[:2]:
                            f.write(f"  Original:  {change['original']}\n")
                            f.write(f"  Corrected: {change['corrected']}\n")
                        if len(changes) > 2:
                            f.write(f"  ... and {len(changes) - 2} more occurrences\n")
                    f.write("\n")
            
            f.write("RECOMMENDATIONS:\n")
            f.write("- Review unknown words - add important ones to glossary\n")
            f.write("- Check if corrections removed important names/terms\n")
            f.write("- Verify new words are correct translations\n")
            f.write("- Consider adjusting confidence thresholds if needed\n")
            
        print(f"Session analysis logged to: {_session_log_data['log_file']}")
    except Exception as e:
        print(f"Warning: Could not write session log: {e}")


# Keep the old function name for compatibility but redirect to new system
def log_names_and_unknown_words(original_lines: list, corrected_lines: list, log_file: str = "correction_log.txt") -> None:
    """
    Compatibility wrapper - now accumulates data instead of immediately writing.
    """
    accumulate_correction_data(original_lines, corrected_lines)


# Global callback manager instance
cli_callbacks = CLICallbackManager()


# Convenience functions for direct use
def on_cli_start(input_file: str, src_lang: str, tgt_lang: str, output_file: str = None):
    """Convenience function to trigger CLI start event."""
    cli_callbacks.on_start(input_file, src_lang, tgt_lang, output_file)


def on_cli_progress(current: int, total: int, stage: str = "processing"):
    """Convenience function to trigger CLI progress event."""
    cli_callbacks.on_progress(current, total, stage)


def on_cli_finish(output_file: str, total_lines: int, duration: float = None):
    """Convenience function to trigger CLI finish event."""
    cli_callbacks.on_finish(output_file, total_lines, duration)


def on_cli_error(error_msg: str, input_file: str = None):
    """Convenience function to trigger CLI error event."""
    cli_callbacks.on_error(error_msg, input_file)


def register_cli_callback(event_type: str, callback: Callable[[CLIEventData], None]):
    """Convenience function to register a CLI callback."""
    cli_callbacks.register_callback(event_type, callback)