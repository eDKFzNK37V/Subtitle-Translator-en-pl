"""
Polish morphology and conjugation improvements for subtitle translation.
This module provides enhanced Polish language processing capabilities.
"""

import re
from typing import Dict, List, Tuple

# Polish verb conjugation patterns and corrections
POLISH_VERB_PATTERNS = {
    # Common verb ending corrections for person/number agreement
    # Present tense patterns
    'jestem': ['jest', 'jesteś', 'jesteśmy', 'jesteście', 'są'],
    'mam': ['ma', 'masz', 'mamy', 'macie', 'mają'],
    'robię': ['robi', 'robisz', 'robimy', 'robicie', 'robią'],
    'idę': ['idzie', 'idziesz', 'idziemy', 'idziecie', 'idą'],
    'widzę': ['widzi', 'widzisz', 'widzimy', 'widzicie', 'widzą'],
    
    # Past tense patterns (common corrections)
    'robiłem': ['robił', 'robiła', 'robiliśmy', 'robiłyście', 'robili'],
    'byłem': ['był', 'była', 'byliśmy', 'byłyście', 'byli'],
    'szedłem': ['szedł', 'szła', 'szliśmy', 'szłyście', 'szli'],
}

# Polish noun case patterns (simplified for common cases)
POLISH_NOUN_CASES = {
    # Nominative -> other cases (simplified examples)
    'dom': ['domu', 'domowi', 'dom', 'domem', 'domu', 'domu'],
    'kobieta': ['kobiety', 'kobiecie', 'kobietę', 'kobietą', 'kobiecie', 'kobieto'],
    'człowiek': ['człowieka', 'człowiekowi', 'człowieka', 'człowiekiem', 'człowieku', 'człowieku'],
    'dziecko': ['dziecka', 'dziecku', 'dziecko', 'dzieckiem', 'dziecku', 'dziecko'],
}

# Common Polish adjective agreement patterns
POLISH_ADJECTIVE_AGREEMENT = {
    # Masculine/feminine/neuter patterns
    'dobry': ['dobra', 'dobre', 'dobrzy', 'dobre'],  # m.sg, f.sg, n.sg, m.pl, f/n.pl
    'wielki': ['wielka', 'wielkie', 'wielcy', 'wielkie'],
    'nowy': ['nowa', 'nowe', 'nowi', 'nowe'],
    'stary': ['stara', 'stare', 'starzy', 'stare'],
    'młody': ['młoda', 'młode', 'młodzi', 'młode'],
}

# Common grammatical error patterns in Polish translations
POLISH_GRAMMAR_FIXES = {
    # Common translation errors
    r'\bja jestem\b': 'jestem',  # Remove redundant pronoun
    r'\bty jesteś\b': 'jesteś',
    r'\bon jest\b': 'jest',
    r'\bona jest\b': 'jest',
    r'\bmy jesteśmy\b': 'jesteśmy',
    r'\bwy jesteście\b': 'jesteście',
    r'\boni są\b': 'są',
    
    # Article removal (Polish doesn't have articles)
    r'\b(ten|ta|to)\s+(?=\w)': '',  # Remove unnecessary demonstratives used as articles
    
    # Common preposition fixes
    r'\bna dom\b': 'do domu',  # to home
    r'\bw dom\b': 'do domu',   # to home
    r'\bna praca\b': 'do pracy',  # to work
    
    # Number agreement fixes (simplified)
    r'\b(\d+)\s+rok\b': r'\1 lat',  # years (for numbers > 1)
    r'\b(\d+)\s+dzień\b': r'\1 dni',  # days
}

# Polish-specific punctuation and formatting
POLISH_PUNCTUATION_RULES = {
    # Proper spacing for Polish punctuation
    r'\s+([,.!?;:])': r'\1',  # Remove space before punctuation
    r'([,.!?;:])\s*([,.!?;:])': r'\1 \2',  # Space between punctuation marks
    r'\?\s*!': '?!',  # Combine question and exclamation
    r'!\s*\?': '!?',  # Combine exclamation and question
    
    # Polish quotation marks
    r'"([^"]*)"': r'„\1"',  # Convert to Polish quotation marks
    r"'([^']*)'": r'„\1"',  # Convert single quotes to Polish quotes
}

def enhance_polish_conjugation(text: str) -> str:
    """
    Enhance Polish text with improved conjugation and grammar.
    
    Args:
        text: Input Polish text to improve
        
    Returns:
        Enhanced text with better Polish grammar
    """
    if not text or not text.strip():
        return text
    
    enhanced = text
    
    # Apply grammar fixes
    for pattern, replacement in POLISH_GRAMMAR_FIXES.items():
        enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
    
    # Apply punctuation rules
    for pattern, replacement in POLISH_PUNCTUATION_RULES.items():
        enhanced = re.sub(pattern, replacement, enhanced)
    
    # Fix common verb conjugation issues
    enhanced = _fix_verb_conjugation(enhanced)
    
    # Fix noun-adjective agreement
    enhanced = _fix_adjective_agreement(enhanced)
    
    return enhanced.strip()

def _fix_verb_conjugation(text: str) -> str:
    """Fix common Polish verb conjugation errors."""
    # Simple heuristic-based fixes for common patterns
    
    # Fix "ja + verb" patterns (remove redundant pronoun)
    text = re.sub(r'\bja\s+(jestem|mam|robię|idę|widzę)', r'\1', text, flags=re.IGNORECASE)
    
    # Fix third person agreement
    text = re.sub(r'\bon\s+są\b', 'oni są', text, flags=re.IGNORECASE)
    text = re.sub(r'\bona\s+są\b', 'one są', text, flags=re.IGNORECASE)
    
    return text

def _fix_adjective_agreement(text: str) -> str:
    """Fix basic Polish adjective-noun agreement."""
    # This is a simplified version - in practice, full Polish morphology is very complex
    
    # Fix some common patterns
    text = re.sub(r'\bdobre\s+mężczyzna\b', 'dobry mężczyzna', text, flags=re.IGNORECASE)
    text = re.sub(r'\bdobry\s+kobieta\b', 'dobra kobieta', text, flags=re.IGNORECASE)
    text = re.sub(r'\bdobry\s+dziecko\b', 'dobre dziecko', text, flags=re.IGNORECASE)
    
    return text

def improve_polish_style(text: str) -> str:
    """
    Improve Polish text style for more natural subtitle language.
    
    Args:
        text: Input Polish text
        
    Returns:
        Text with improved Polish style
    """
    if not text or not text.strip():
        return text
    
    styled = text
    
    # Make more conversational for subtitles
    conversational_replacements = {
        r'\bczy możesz\b': 'możesz',  # "can you" -> "you can" (more direct)
        r'\bczy mogę\b': 'mogę',     # "can I" -> "I can"
        r'\bproszę bardzo\b': 'proszę',  # "you're very welcome" -> "please"
        r'\bdziękuję bardzo\b': 'dzięki',  # "thank you very much" -> "thanks"
        r'\bprzepraszam bardzo\b': 'przepraszam',  # "I'm very sorry" -> "sorry"
    }
    
    for pattern, replacement in conversational_replacements.items():
        styled = re.sub(pattern, replacement, styled, flags=re.IGNORECASE)
    
    # Improve word order for more natural Polish
    styled = _improve_word_order(styled)
    
    return styled

def _improve_word_order(text: str) -> str:
    """Improve Polish word order for more natural flow."""
    # Simple patterns for better word order
    
    # Move negation closer to verb
    text = re.sub(r'\bnie\s+(.+?)\s+(jest|są|było|będzie)\b', r'\2 nie \1', text, flags=re.IGNORECASE)
    
    # Improve question word order  
    text = re.sub(r'\bco\s+ty\s+', 'co ', text, flags=re.IGNORECASE)
    text = re.sub(r'\bkiedy\s+ty\s+', 'kiedy ', text, flags=re.IGNORECASE)
    
    return text