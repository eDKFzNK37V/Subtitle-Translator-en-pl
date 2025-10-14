#!/usr/bin/env python3
"""
Unit tests for the Subtitle Translator (without requiring model installation).
Tests the parsing, tag protection, and restoration logic.
"""

import unittest
import sys
import os
from typing import Any

# Mock the imports that require heavy dependencies
class MockTokenizer:
    def __init__(self, *args: Any, **kwargs: Any):
        self.src_lang = None
        self.lang_code_to_id = {}
    
    def __call__(self, text: Any, **kwargs: Any) -> dict:
        return {"input_ids": [[1, 2, 3]]}
    
    def batch_decode(self, tokens: Any, **kwargs: Any) -> list:
        return ["mocked translation"]
    
    def convert_tokens_to_ids(self, token: str) -> int:
        return 123

class MockModel:
    def __init__(self, *args: Any, **kwargs: Any):
        pass
    
    def to(self, device: str) -> 'MockModel':
        return self
    
    def eval(self) -> 'MockModel':
        return self
    
    def generate(self, **kwargs: Any) -> list:
        return [[1, 2, 3]]

# Create mock torch module
mock_torch = type('MockTorch', (), {
    'cuda': type('cuda', (), {'is_available': lambda: False})(),
    'no_grad': lambda: type('context', (), {'__enter__': lambda self: None, '__exit__': lambda self, *args: None})(),
})()
sys.modules['torch'] = mock_torch  # type: ignore

# Create mock transformers module
mock_transformers = type('MockTransformers', (), {
    'AutoTokenizer': type('AutoTokenizer', (), {
        'from_pretrained': staticmethod(lambda x: MockTokenizer())
    })(),
    'AutoModelForSeq2SeqLM': type('AutoModelForSeq2SeqLM', (), {
        'from_pretrained': staticmethod(lambda x: MockModel())
    })()
})()
sys.modules['transformers'] = mock_transformers  # type: ignore

# Create mock tqdm module
mock_tqdm = type('MockTqdm', (), {
    'tqdm': lambda x, **kwargs: x
})()
sys.modules['tqdm'] = mock_tqdm  # type: ignore

# Now import from main.py
try:
    from main import SubtitleTranslator
except ImportError:
    # Fallback for old structure
    from translate_ass import ASSTranslator as SubtitleTranslator  # type: ignore


class TestSubtitleTranslator(unittest.TestCase):
    """Test cases for SubtitleTranslator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Note: We can't actually initialize the translator without the model
        # so we'll test individual methods
        pass
    
    def test_tag_pattern(self):
        """Test that tag pattern matches correctly."""
        import re
        pattern = SubtitleTranslator.TAG_OR_ESCAPE
        
        # Test ASS tags
        self.assertTrue(pattern.search(r'{\pos(320,240)}'))
        self.assertTrue(pattern.search(r'{\an8}'))
        
        # Test line break
        self.assertTrue(pattern.search(r'\N'))
        self.assertTrue(pattern.search(r'\n'))
        
        # Test other escapes
        self.assertTrue(pattern.search(r'\H'))
        self.assertTrue(pattern.search(r'\h'))
    
    def test_protect_and_restore_tags(self):
        """Test tag protection and restoration."""
        translator = SubtitleTranslator.__new__(SubtitleTranslator)
        
        # Test with ASS tags
        text = r"{\pos(320,240)}This is text{\an8} with tags."
        protected, tags = translator.protect_tags(text)
        
        self.assertIn("<TAG0>", protected)
        self.assertIn("<TAG1>", protected)
        self.assertEqual(len(tags), 2)
        self.assertEqual(tags[0], r'{\pos(320,240)}')
        self.assertEqual(tags[1], r'{\an8}')
        
        # Test restoration
        restored = translator.restore_tags(protected, tags)
        self.assertEqual(restored, text)
    
    def test_insert_n_tags(self):
        """Test \\N tag insertion."""
        translator = SubtitleTranslator.__new__(SubtitleTranslator)
        
        # Test insertion at specific index
        text = "This is a long subtitle line"
        result = translator.insert_n_tags(text, n_count=1, word_idx=4)
        self.assertIn(r'\N', result)
        
        # Test with no tags
        result = translator.insert_n_tags(text, n_count=0, word_idx=4)
        self.assertEqual(result, text)
        
        # Test with auto (word_idx=0) - should insert in middle
        result = translator.insert_n_tags(text, n_count=1, word_idx=0)
        self.assertIn(r'\N', result)
    
    def test_lang_codes(self):
        """Test language code mappings."""
        codes = SubtitleTranslator.LANG_CODES
        
        # Check essential languages are present
        self.assertIn('en', codes)
        self.assertIn('pl', codes)
        self.assertIn('ja', codes)
        self.assertIn('fr', codes)
        self.assertIn('de', codes)
        
        # Check NLLB format
        self.assertEqual(codes['en'], 'eng_Latn')
        self.assertEqual(codes['pl'], 'pol_Latn')


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSubtitleTranslator)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
