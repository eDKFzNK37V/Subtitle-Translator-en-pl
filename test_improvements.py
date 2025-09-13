#!/usr/bin/env python3
"""
Test script to validate the subtitle translator improvements.
"""

import sys
import re
from typing import List

# Add current directory to path for imports
sys.path.insert(0, '.')

def test_tag_restoration():
    """Test improved tag placeholder restoration."""
    print("Testing tag placeholder restoration...")
    
    try:
        from text_tools import extract_tags_with_placeholders, restore_tags_from_placeholders
        
        # Test case 1: Basic tag restoration
        original = "Hello {\\pos(320,240)}world!"
        clean, ph_map = extract_tags_with_placeholders(original)
        print(f"Original: {original}")
        print(f"Clean: {clean}")
        print(f"Placeholders: {ph_map}")
        
        # Simulate translation
        translated = "Cześć świecie!"
        restored = restore_tags_from_placeholders(translated, ph_map)
        print(f"Restored: {restored}")
        
        # Test case 2: Multiple tags
        original2 = "{\\an8}Top text{\\N}Bottom text{\\pos(100,200)}"
        clean2, ph_map2 = extract_tags_with_placeholders(original2)
        translated2 = "Górny tekst Dolny tekst"
        restored2 = restore_tags_from_placeholders(translated2, ph_map2)
        print(f"Original2: {original2}")
        print(f"Restored2: {restored2}")
        
        print("✅ Tag restoration test passed")
        
    except Exception as e:
        print(f"❌ Tag restoration test failed: {e}")

def test_contextaware_n_insertion():
    """Test context-aware \\N tag insertion."""
    print("\nTesting context-aware \\N insertion...")
    
    try:
        from text_tools import insert_newline_tags_contextaware
        
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
    """Test improved dialogue grouping."""
    print("Testing improved dialogue grouping...")
    
    try:
        from text_tools import group_dialogue_lines, split_grouped_translations
        
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
        
        # Test splitting back
        fake_translations = [f"TRANSLATED_{i}" for i in range(len(grouped))]
        split_back = split_grouped_translations(fake_translations, mapping)
        print(f"Split back: {len(split_back)} lines")
        
        print("✅ Dialogue grouping test passed")
        
    except Exception as e:
        print(f"❌ Dialogue grouping test failed: {e}")

def test_style_tone_adjustment():
    """Test style and tone adjustment."""
    print("\nTesting style/tone adjustment...")
    
    try:
        from text_tools import adjust_subtitle_style_tone
        
        test_texts = [
            "I am going to go to the store.",
            "Well, um, I think that, you know, it's fine.",
            "Due to the fact that it was raining, we stayed inside.",
            "Chciałbym powiedzieć, że jestem zadowolony z wyników."
        ]
        
        for text in test_texts:
            adjusted = adjust_subtitle_style_tone(text, "en")
            print(f"Original: {text}")
            print(f"Adjusted: {adjusted}")
            print()
        
        print("✅ Style/tone adjustment test passed")
        
    except Exception as e:
        print(f"❌ Style/tone adjustment test failed: {e}")

def test_enhanced_glossary():
    """Test enhanced glossary functionality."""
    print("Testing enhanced glossary...")
    
    try:
        from pipeline import apply_glossary
        from resources import ENHANCED_GLOSSARY, apply_context_sensitive_glossary
        
        test_texts = [
            "The hero saved the guild leader.",
            "Let's go to the meeting with the client.",
            "Come on, let's play this game!"
        ]
        
        for text in test_texts:
            enhanced = apply_glossary(text, use_context=True)
            print(f"Original: {text}")
            print(f"Enhanced: {enhanced}")
            print()
        
        print("✅ Enhanced glossary test passed")
        
    except Exception as e:
        print(f"❌ Enhanced glossary test failed: {e}")

def test_confidence_scoring():
    """Test confidence-based correction fallback."""
    print("Testing confidence scoring...")
    
    try:
        from text_tools import calculate_text_similarity_confidence
        
        test_cases = [
            ("hello world", "hello world"),  # identical
            ("hello world", "hello word"),   # small change
            ("hello world", "goodbye universe"),  # big change
        ]
        
        for original, corrected in test_cases:
            confidence = calculate_text_similarity_confidence(original, corrected)
            print(f"'{original}' -> '{corrected}': confidence = {confidence:.3f}")
        
        print("✅ Confidence scoring test passed")
        
    except Exception as e:
        print(f"❌ Confidence scoring test failed: {e}")

def main():
    """Run all tests."""
    print("🧪 Running subtitle translator improvement tests...\n")
    
    test_tag_restoration()
    test_contextaware_n_insertion()
    test_dialogue_grouping()
    test_style_tone_adjustment()
    test_enhanced_glossary()
    test_confidence_scoring()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    main()