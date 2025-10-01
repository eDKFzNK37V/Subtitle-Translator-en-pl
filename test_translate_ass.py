#!/usr/bin/env python3
"""
Unit tests for the ASS translator (without requiring model installation).
Tests the parsing, tag protection, and restoration logic.
"""

import unittest
import sys
import os

# Mock the imports that require heavy dependencies
class MockTokenizer:
    def __init__(self, *args, **kwargs):
        self.src_lang = None
        self.lang_code_to_id = {}
    
    def __call__(self, text, **kwargs):
        return {"input_ids": [[1, 2, 3]]}
    
    def batch_decode(self, tokens, **kwargs):
        return ["mocked translation"]

class MockModel:
    def __init__(self, *args, **kwargs):
        pass
    
    def to(self, device):
        return self
    
    def eval(self):
        return self
    
    def generate(self, **kwargs):
        return [[1, 2, 3]]

# Create mock torch module
mock_torch = type('MockTorch', (), {
    'cuda': type('cuda', (), {'is_available': lambda: False})(),
    'no_grad': lambda: type('context', (), {'__enter__': lambda self: None, '__exit__': lambda self, *args: None})(),
})()
sys.modules['torch'] = mock_torch

# Create mock transformers module
mock_transformers = type('MockTransformers', (), {
    'AutoTokenizer': type('AutoTokenizer', (), {
        'from_pretrained': staticmethod(lambda x: MockTokenizer())
    })(),
    'AutoModelForSeq2SeqLM': type('AutoModelForSeq2SeqLM', (), {
        'from_pretrained': staticmethod(lambda x: MockModel())
    })()
})()
sys.modules['transformers'] = mock_transformers

# Create mock tqdm module
mock_tqdm = type('MockTqdm', (), {
    'tqdm': lambda x, **kwargs: x
})()
sys.modules['tqdm'] = mock_tqdm

# Now import from main.py instead of translate_ass
try:
    from main import SubtitleTranslator as ASSTranslator
except ImportError:
    # Fallback for old structure
    from translate_ass import ASSTranslator  # type: ignore


class TestASSTranslator(unittest.TestCase):
    """Test cases for ASSTranslator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Note: We can't actually initialize the translator without the model
        # so we'll test individual methods
        pass
    
    def test_tag_pattern(self):
        """Test that tag pattern matches correctly."""
        import re
        pattern = ASSTranslator.TAG_PATTERN
        
        # Test italic tags
        self.assertTrue(pattern.search(r'{\i1}'))
        self.assertTrue(pattern.search(r'{\i0}'))
        
        # Test bold tags
        self.assertTrue(pattern.search(r'{\b1}'))
        
        # Test line break
        self.assertTrue(pattern.search(r'\N'))
        
        # Test color tags
        self.assertTrue(pattern.search(r'{\c&HFF0000&}'))
        
        # Test reset tag
        self.assertTrue(pattern.search(r'{\r}'))
    
    def test_extract_text_from_dialogue(self):
        """Test extraction of text from dialogue lines."""
        translator = ASSTranslator.__new__(ASSTranslator)
        
        # Test normal dialogue line
        line = "Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Hello, world!\n"
        prefix, text, suffix = translator.extract_text_from_dialogue(line)
        
        self.assertEqual(prefix, "Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,")
        self.assertEqual(text, "Hello, world!")
        self.assertEqual(suffix, "\n")
    
    def test_protect_and_restore_tags(self):
        """Test tag protection and restoration."""
        translator = ASSTranslator.__new__(ASSTranslator)
        
        # Test with italic tags
        text = r"{\i1}This is italic{\i0} and this is normal."
        protected, tags = translator.protect_tags(text)
        
        self.assertIn("<TAG0>", protected)
        self.assertIn("<TAG1>", protected)
        self.assertEqual(len(tags), 2)
        self.assertEqual(tags[0], r"{\i1}")
        self.assertEqual(tags[1], r"{\i0}")
        
        # Restore tags
        restored = translator.restore_tags(protected, tags)
        self.assertEqual(restored, text)
    
    def test_protect_tags_with_line_breaks(self):
        """Test tag protection with line breaks."""
        translator = ASSTranslator.__new__(ASSTranslator)
        
        text = r"First line\NSecond line"
        protected, tags = translator.protect_tags(text)
        
        self.assertIn("<TAG0>", protected)
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0], r"\N")
    
    def test_protect_tags_complex(self):
        """Test tag protection with complex formatting."""
        translator = ASSTranslator.__new__(ASSTranslator)
        
        text = r"{\b1}Bold{\b0}\N{\i1}Italic{\i0} {\c&HFF0000&}Red{\r}"
        protected, tags = translator.protect_tags(text)
        
        # Should have 7 tags
        self.assertEqual(len(tags), 7)
        
        # Verify order
        self.assertEqual(tags[0], r"{\b1}")
        self.assertEqual(tags[1], r"{\b0}")
        self.assertEqual(tags[2], r"\N")
        self.assertEqual(tags[3], r"{\i1}")
        self.assertEqual(tags[4], r"{\i0}")
        
        # Restore and verify
        restored = translator.restore_tags(protected, tags)
        self.assertEqual(restored, text)
    
    def test_parse_ass_file(self):
        """Test parsing of .ass file."""
        translator = ASSTranslator.__new__(ASSTranslator)
        
        # Create a test file
        test_file = '/tmp/test_parse.ass'
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("""[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Test dialogue 1
Dialogue: 0,0:00:05.00,0:00:08.00,Default,,0,0,0,,Test dialogue 2
""")
        
        header, dialogues = translator.parse_ass_file(test_file)
        
        # Clean up
        os.remove(test_file)
        
        # Verify
        self.assertTrue(any('[Script Info]' in line for line in header))
        self.assertTrue(any('[Events]' in line for line in header))
        self.assertEqual(len(dialogues), 2)
        self.assertTrue(dialogues[0].startswith('Dialogue:'))
        self.assertIn('Test dialogue 1', dialogues[0])
        self.assertIn('Test dialogue 2', dialogues[1])


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestASSTranslator)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
