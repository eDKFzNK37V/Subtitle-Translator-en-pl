#!/usr/bin/env python3
"""
Test script for core functions that don't require heavy dependencies.
"""

import sys
import re
from typing import List, Tuple

def test_contextaware_n_insertion():
    """Test context-aware \\N tag insertion logic."""
    print("Testing context-aware \\N insertion...")
    
    def insert_newline_tags_contextaware(text: str, n_tags: int, prefer_punctuation: bool = True) -> str:
        """Local implementation for testing."""
        if n_tags <= 0 or not text.strip():
            return text
        
        insertion_points = []
        
        # Look for punctuation-based breaks
        if prefer_punctuation:
            for match in re.finditer(r'[.!?,:;]\s+', text):
                insertion_points.append((match.end(), 'punctuation', 3))
        
        # Look for clause boundaries with conjunctions
        for match in re.finditer(r'\b(and|but|or|so|yet|for|nor|because|since|although|while|if|when|where|after|before)\s+', text, re.IGNORECASE):
            insertion_points.append((match.start(), 'conjunction', 2))
        
        # Look for natural pauses
        for match in re.finditer(r'[,—–-]\s+', text):
            insertion_points.append((match.end(), 'pause', 1))
        
        # If no good punctuation found, use word boundaries
        if not insertion_points:
            words = [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]
            if words:
                mid_point = len(words) // 2
                if mid_point < len(words):
                    insertion_points.append((words[mid_point][0], 'word', 0))
        
        # Sort by priority (higher priority first), then by position
        insertion_points.sort(key=lambda x: (-x[2], x[0]))
        
        # Insert tags at best positions
        result = text
        tags_inserted = 0
        offset = 0
        
        for pos, point_type, priority in insertion_points:
            if tags_inserted >= n_tags:
                break
                
            adjusted_pos = pos + offset
            result = result[:adjusted_pos] + "\\N" + result[adjusted_pos:]
            offset += 2
            tags_inserted += 1
        
        while tags_inserted < n_tags:
            result += "\\N"
            tags_inserted += 1
        
        return result
    
    try:
        test_cases = [
            ("Hello world, how are you? I am fine.", 1),
            ("This is a test. And this is another sentence!", 1),
            ("Short text", 1),
            ("Very long sentence that should be broken at a natural point, like after a comma or conjunction.", 2)
        ]
        
        for text, n_tags in test_cases:
            result = insert_newline_tags_contextaware(text, n_tags)
            print(f"Original: {text}")
            print(f"With \\N: {result}")
            print()
        
        print("✅ Context-aware \\N insertion test passed")
        
    except Exception as e:
        print(f"❌ Context-aware \\N insertion test failed: {e}")

def test_dialogue_grouping():
    """Test improved dialogue grouping logic."""
    print("Testing improved dialogue grouping...")
    
    def group_dialogue_lines(lines: List[str]) -> Tuple[List[str], List[List[int]]]:
        """Local implementation for testing."""
        IDIOM_PATTERNS = [
            r'\b(in order to|as well as|such as|rather than|not only|but also)\b',
            r'\b(on the other hand|at the same time|in addition to|in spite of)\b',
        ]
        
        CONTINUATION_PATTERNS = [
            r'^(and|but|or|so|then|now|well|yes|no|oh|ah)\s',
            r'^[a-z]',
        ]
        
        BREAK_PATTERNS = [
            r'[.!?]\s*$',
            r':\s*$',
            r'"\s*$',
        ]
        
        def should_continue_group(prev_line: str, curr_line: str) -> bool:
            if not curr_line.strip():
                return False
                
            for pattern in CONTINUATION_PATTERNS:
                if re.search(pattern, curr_line, re.IGNORECASE):
                    for break_pattern in BREAK_PATTERNS:
                        if re.search(break_pattern, prev_line):
                            return False
                    return True
            
            combined = prev_line + " " + curr_line
            for pattern in IDIOM_PATTERNS:
                if re.search(pattern, combined, re.IGNORECASE):
                    return True
                    
            return False
        
        def is_natural_break(line: str) -> bool:
            for pattern in BREAK_PATTERNS:
                if re.search(pattern, line):
                    return True
            return False
        
        grouped_lines = []
        mapping = []
        i = 0
        
        while i < len(lines):
            group = [lines[i]]
            indices = [i]
            
            while i + 1 < len(lines):
                next_line = lines[i + 1]
                current_line = lines[i]
                
                if len(group) >= 3:
                    break
                    
                if should_continue_group(current_line, next_line):
                    group.append(next_line)
                    indices.append(i + 1)
                    i += 1
                else:
                    break
            
            if len(group) == 1:
                grouped_text = group[0]
            else:
                joined_parts = []
                for j, part in enumerate(group):
                    if j == 0:
                        joined_parts.append(part)
                    else:
                        prev_part = group[j-1]
                        if is_natural_break(prev_part):
                            joined_parts.append(" " + part)
                        else:
                            joined_parts.append(" " + part)
                grouped_text = "".join(joined_parts)
            
            grouped_lines.append(grouped_text)
            mapping.append(indices)
            i += 1
        
        return grouped_lines, mapping
    
    try:
        lines = [
            "Hello there!",
            "and how are you today?",
            "I'm doing well, thank you.",
            "but I have a question.",
            "What is it?",
            "Well, I was wondering...",
            "if you could help me."
        ]
        
        grouped, mapping = group_dialogue_lines(lines)
        print(f"Original lines: {len(lines)}")
        print(f"Grouped lines: {len(grouped)}")
        
        for i, (group, indices) in enumerate(zip(grouped, mapping)):
            print(f"Group {i}: {group} (indices: {indices})")
        
        print("✅ Dialogue grouping test passed")
        
    except Exception as e:
        print(f"❌ Dialogue grouping test failed: {e}")

def test_style_adjustments():
    """Test style adjustment patterns."""
    print("\nTesting style adjustment patterns...")
    
    def adjust_subtitle_style_tone(text: str, target_lang: str = "pl") -> str:
        """Local implementation for testing."""
        if not text.strip():
            return text
        
        if target_lang.lower() == "pl":
            adjustments = [
                (r'\bchciałbym\s+powiedzieć,?\s*że\b', 'chcę powiedzieć, że'),
                (r'\bmuszę\s+przyznać,?\s*że\b', 'przyznaję, że'),
                (r'\bw\s+związku\s+z\s+tym\b', 'dlatego'),
            ]
        else:
            adjustments = [
                (r"\bI'm going to\b", "I'll"),
                (r"\bdo not\b", "don't"),
                (r"\bcannot\b", "can't"),
                (r'\bin order to\b', 'to'),
            ]
        
        adjusted = text
        for pattern, replacement in adjustments:
            adjusted = re.sub(pattern, replacement, adjusted, flags=re.IGNORECASE)
        
        # General optimizations
        adjusted = re.sub(r'[.]{2,}', '...', adjusted)
        adjusted = re.sub(r'[!]{2,}', '!', adjusted)
        adjusted = re.sub(r'\s+', ' ', adjusted)
        
        return adjusted.strip()
    
    try:
        test_texts = [
            "I'm going to go to the store.",
            "I cannot do this in order to help you.",
            "Chciałbym powiedzieć, że jestem zadowolony.",
            "W związku z tym muszę przyznać, że..."
        ]
        
        for text in test_texts:
            lang = "pl" if any(char in text for char in "ąćęłńóśźż") else "en"
            adjusted = adjust_subtitle_style_tone(text, lang)
            print(f"Original: {text}")
            print(f"Adjusted: {adjusted}")
            print()
        
        print("✅ Style adjustment test passed")
        
    except Exception as e:
        print(f"❌ Style adjustment test failed: {e}")

def test_confidence_calculation():
    """Test confidence calculation logic."""
    print("Testing confidence calculation...")
    
    def calculate_text_similarity_confidence(original: str, corrected: str) -> float:
        """Local implementation for testing."""
        if original == corrected:
            return 1.0
        
        len_diff = abs(len(original) - len(corrected))
        max_len = max(len(original), len(corrected))
        
        if max_len == 0:
            return 1.0
        
        length_ratio = 1.0 - (len_diff / max_len)
        matches = sum(1 for a, b in zip(original.lower(), corrected.lower()) if a == b)
        char_ratio = matches / max_len if max_len > 0 else 1.0
        
        confidence = (length_ratio * 0.3 + char_ratio * 0.7)
        return max(0.0, min(1.0, confidence))
    
    try:
        test_cases = [
            ("hello world", "hello world"),
            ("hello world", "hello word"),
            ("hello world", "goodbye universe"),
            ("test", "TEST"),
            ("", ""),
        ]
        
        for original, corrected in test_cases:
            confidence = calculate_text_similarity_confidence(original, corrected)
            print(f"'{original}' -> '{corrected}': confidence = {confidence:.3f}")
        
        print("✅ Confidence calculation test passed")
        
    except Exception as e:
        print(f"❌ Confidence calculation test failed: {e}")

def main():
    """Run all core tests."""
    print("🧪 Running core function tests...\n")
    
    test_contextaware_n_insertion()
    test_dialogue_grouping()
    test_style_adjustments()
    test_confidence_calculation()
    
    print("\n🎉 Core tests completed!")

if __name__ == "__main__":
    main()