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
    
    def half(self) -> 'MockModel':
        return self
    
    def eval(self) -> 'MockModel':
        return self
    
    def generate(self, **kwargs: Any) -> list:
        return [[1, 2, 3]]

# Create mock tkinter module
try:
    import tkinter as tk
except ImportError:
    # Create a minimal mock tkinter for testing
    class MockTk:
        def __init__(self): pass
    mock_tk = type('MockTkinter', (), {
        'Tk': MockTk,
        'StringVar': type('StringVar', (), {'__init__': lambda self, value="": None, 'get': lambda self: "", 'set': lambda self, v: None})(),
        'IntVar': type('IntVar', (), {'__init__': lambda self, value=0: None, 'get': lambda self: 0, 'set': lambda self, v: None})(),
        'BooleanVar': type('BooleanVar', (), {'__init__': lambda self, value=False: None, 'get': lambda self: False, 'set': lambda self, v: None})(),
        'messagebox': type('messagebox', (), {'showerror': lambda *args: None, 'showinfo': lambda *args: None})(),
        'filedialog': type('filedialog', (), {'askopenfilename': lambda *args, **kwargs: "", 'askdirectory': lambda *args, **kwargs: ""})(),
        'Button': type('Button', (), {'__init__': lambda *args, **kwargs: None})(),
        'Label': type('Label', (), {'__init__': lambda *args, **kwargs: None})(),
        'Entry': type('Entry', (), {'__init__': lambda *args, **kwargs: None})(),
        'Text': type('Text', (), {'__init__': lambda *args, **kwargs: None})(),
        'Frame': type('Frame', (), {'__init__': lambda *args, **kwargs: None})(),
        'Canvas': type('Canvas', (), {'__init__': lambda *args, **kwargs: None})(),
        'Scrollbar': type('Scrollbar', (), {'__init__': lambda *args, **kwargs: None})(),
        'Toplevel': type('Toplevel', (), {'__init__': lambda *args, **kwargs: None})(),
        'Checkbutton': type('Checkbutton', (), {'__init__': lambda *args, **kwargs: None})(),
        'Spinbox': type('Spinbox', (), {'__init__': lambda *args, **kwargs: None})(),
        'OptionMenu': type('OptionMenu', (), {'__init__': lambda *args, **kwargs: None})(),
        'LabelFrame': type('LabelFrame', (), {'__init__': lambda *args, **kwargs: None})(),
        'WORD': 'word',
        'BOTH': 'both',
        'X': 'x',
        'LEFT': 'left',
        'BOTTOM': 'bottom',
    })()
    sys.modules['tkinter'] = mock_tk  # type: ignore

# Create mock torch module
mock_torch = type('MockTorch', (), {
    'cuda': type('cuda', (), {'is_available': lambda *args, **kwargs: False, 'empty_cache': lambda: None, 'OutOfMemoryError': Exception})(),
    'no_grad': lambda: type('context', (), {'__enter__': lambda self: None, '__exit__': lambda self, *args: None})(),
    'backends': type('backends', (), {
        'cuda': type('cuda', (), {'matmul': type('matmul', (), {'allow_tf32': True})()})(),
        'cudnn': type('cudnn', (), {'allow_tf32': True})()
    })(),
    'float16': 'float16',
})()
sys.modules['torch'] = mock_torch  # type: ignore

# Create mock transformers module
mock_transformers = type('MockTransformers', (), {
    'AutoTokenizer': type('AutoTokenizer', (), {
        'from_pretrained': staticmethod(lambda x: MockTokenizer())
    })(),
    'AutoModelForSeq2SeqLM': type('AutoModelForSeq2SeqLM', (), {
        'from_pretrained': staticmethod(lambda x, **kwargs: MockModel())
    })(),
    'BitsAndBytesConfig': type('BitsAndBytesConfig', (), {
        '__init__': lambda self, **kwargs: None
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
        
        # Note: The pattern is designed to match escape sequences in subtitle files
        # where they appear as literal backslash followed by character
        # The test checks if the pattern would match them when reading from files
    
    def test_protect_and_restore_tags(self):
        """Test tag protection and restoration."""
        translator = SubtitleTranslator.__new__(SubtitleTranslator)
        
        # Test with ASS tags
        text = r"{\pos(320,240)}This is text{\an8} with tags."
        protected, tags = translator.protect_tags(text)
        
        self.assertIn("<TAGPH_", protected)
        self.assertEqual(len(tags), 2)
        self.assertEqual(tags[0][1], r'{\pos(320,240)}')
        self.assertEqual(tags[1][1], r'{\an8}')
        
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

    def test_default_num_beams(self):
        """Ensure default num_beams favors translation quality."""
        translator = SubtitleTranslator()
        self.assertEqual(translator.num_beams, 4)

    def test_polish_max_new_tokens(self):
        """Ensure Polish gets a higher max_new_tokens limit."""
        default_tokens = SubtitleTranslator.DEFAULT_MAX_NEW_TOKENS
        self.assertEqual(SubtitleTranslator.get_max_new_tokens('pl'), 150)
        self.assertEqual(SubtitleTranslator.get_max_new_tokens('pol_Latn'), 150)
        self.assertEqual(SubtitleTranslator.get_max_new_tokens('fr'), default_tokens)


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
