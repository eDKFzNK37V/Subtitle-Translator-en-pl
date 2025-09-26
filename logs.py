
import os
import re
from datetime import datetime

class SubtitleLogger:
    def __init__(self, file_path, target_lang, idx_map=None):
        self.file_path = file_path
        self.target_lang = target_lang
        self.idx_map = idx_map or []
        self.entries = []
        self.log_txt = self._make_log_path(file_path)

    def _make_log_path(self, file_path):
        base, _ = os.path.splitext(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{base}_log_{timestamp}.txt"

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
        """
        with open(self.log_txt, "w", encoding="utf-8-sig") as f:
            f.write(f"Log for: {self.file_path}\n")
            f.write(f"Target language: {self.target_lang}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")

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