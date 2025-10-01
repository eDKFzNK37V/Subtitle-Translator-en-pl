"""
Simplified Polish morphology enhancements.
Provides basic Polish-specific text improvements.
"""

import re


def enhance_polish_conjugation(text: str) -> str:
    """
    Basic Polish conjugation improvements.
    Simplified version that handles common cases only.
    """
    if not text:
        return text
    
    # Remove redundant "ja jestem" (I am) - Polish often omits the pronoun
    text = re.sub(r'\bja jestem\b', 'jestem', text, flags=re.IGNORECASE)
    
    # Fix common verb conjugation issues
    text = re.sub(r'\bmnie jest\b', 'jestem', text, flags=re.IGNORECASE)
    
    return text


def improve_polish_style(text: str) -> str:
    """
    Basic Polish style improvements.
    Simplified version for common style adjustments.
    """
    if not text:
        return text
    
    # Polish quotation marks
    text = re.sub(r'"([^"]*)"', r'„\1"', text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    
    return text.strip()


def validate_polish_text(text: str) -> tuple:
    """
    Basic validation of Polish text.
    Returns (is_valid, list_of_issues).
    """
    issues = []
    
    # Check for basic issues
    if not text or not text.strip():
        issues.append("Empty text")
    
    # Check for unbalanced quotes
    if text.count('"') % 2 != 0:
        issues.append("Unbalanced quotes")
    
    return (len(issues) == 0, issues)
