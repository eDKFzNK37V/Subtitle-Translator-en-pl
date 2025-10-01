# Subtitle-Translator-en-pl: Copilot AI Agent Guide

## Architecture Overview

**Unified Single-File Application**

This project has been completely restructured from a complex multi-file architecture (~4,216 lines, 13 files) into a single self-contained application (569 lines in `main.py`).

### Core Components

- **Entry point:** `main.py` - Single file containing ALL functionality
  - `SubtitleTranslator` class - NLLB model and translation engine
  - `run_gui()` function - Tkinter-based GUI with threading
  - `run_cli()` function - Command-line interface
  
### Key Features

1. **Self-contained** - No local module dependencies, everything in one file
2. **Multi-format support** - .ass, .srt, and .txt files
3. **Tag preservation** - Automatic protection of subtitle formatting tags
4. **Threading** - Non-blocking GUI with background translation
5. **Review window** - Edit translations before saving
6. **\N tag insertion** - Line break control for .ass files

## Architecture & Data Flow

**Translation Pipeline (all in main.py):**

1. **Load file** → Detect format (.ass, .srt, .txt)
2. **Extract text** → Parse dialogue/content, separate from metadata
3. **Protect tags** → Replace subtitle tags with placeholders (e.g., `{\pos(x,y)}` → `<TAG0>`)
4. **Translate** → Batch translation using NLLB model
5. **Restore tags** → Replace placeholders with original tags
6. **Insert \N tags** → Add line breaks at specified word index (.ass only)
7. **Save file** → Write translated file with preserved structure

**Class Structure:**

```python
SubtitleTranslator:
  - __init__()              # Load NLLB model
  - protect_tags()          # Replace tags with placeholders
  - restore_tags()          # Restore tags from placeholders
  - insert_n_tags()         # Insert \N line breaks
  - translate()             # Batch translate texts
  - translate_ass_file()    # Handle .ass format
  - translate_srt_file()    # Handle .srt format
  - translate_txt_file()    # Handle .txt format
```

## Developer Workflows

### Running the Application

**GUI Mode (default):**
```bash
python main.py
```

**CLI Mode:**
```bash
# Basic translation
python main.py input.ass --src en --tgt pl

# With \N tag insertion
python main.py input.ass --nwordix 5

# Different formats
python main.py input.srt --src en --tgt ja
python main.py input.txt --src en --tgt fr
```

### Setup & Dependencies

1. **Install Python 3.8+**

2. **Install dependencies:**
```bash
pip install -r requirements.txt

# For CUDA GPU:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# For CPU only:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

3. **Core dependencies (4 packages only):**
   - torch (PyTorch neural models)
   - transformers (HuggingFace NLLB model)
   - tqdm (progress display)
   - sentencepiece (tokenizer)

### Testing

```bash
# Run existing tests
python test_translate_ass.py
```

## Project-Specific Patterns & Conventions

### Tag Handling

**Pattern:** Extract → Translate → Restore

```python
# Extract tags before translation
text = "Hello {\pos(320,240)} world"
protected, tags = translator.protect_tags(text)
# protected = "Hello <TAG0> world"
# tags = ["{\pos(320,240)}"]

# After translation
translated = "Cześć <TAG0> świecie"
final = translator.restore_tags(translated, tags)
# final = "Cześć {\pos(320,240)} świecie"
```

**Supported tag types:**
- ASS formatting: `{\pos(x,y)}`, `{\an8}`, `{\fad(x,y)}`
- Line breaks: `\N`, `\n`
- Other escapes: `\H`, `\h`

### \N Tag Insertion (.ass files only)

```python
# Insert line breaks at word index
text = "This is a long subtitle line"
with_breaks = translator.insert_n_tags(text, n_count=1, word_idx=4)
# Result: "This is a long \N subtitle line"

# word_idx=0 means auto (middle of line)
```

### File Format Handling

**.ass (Advanced SubStation Alpha):**
- Parse dialogue lines: `Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text`
- Extract text (10th field)
- Preserve all metadata and timing
- Support \N tag insertion

**.srt (SubRip):**
- Parse blocks: index, timestamp, text
- Preserve subtitle numbering and timing
- No \N tag support

**.txt (Plain Text):**
- Translate non-empty, non-numeric lines
- Preserve leading/trailing whitespace
- Maintain line structure

### Threading (GUI only)

Translation runs in background thread to keep GUI responsive:

```python
def start_translation():
    def translate_thread():
        # Load model, translate, show review
        pass
    
    thread = threading.Thread(target=translate_thread, daemon=True)
    thread.start()
```

### Supported Languages

Default language codes (extend in `LANG_CODES` dict):
- English (en) → eng_Latn
- Polish (pl) → pol_Latn
- Japanese (ja) → jpn_Jpan
- French (fr) → fra_Latn
- German (de) → deu_Latn

## Code Modification Guidelines

### Adding New Languages

Edit `LANG_CODES` dictionary in `SubtitleTranslator` class:

```python
LANG_CODES = {
    'en': 'eng_Latn',
    'pl': 'pol_Latn',
    # Add new languages here:
    'es': 'spa_Latn',  # Spanish
}
```

### Modifying Translation Parameters

Edit `translate()` method in `SubtitleTranslator`:

```python
generated = self.model.generate(
    **encoded,
    forced_bos_token_id=tgt_id,
    max_length=256,        # Adjust max length
    num_beams=3,           # Adjust beam search
    early_stopping=True
)
```

### Adding GUI Controls

Modify `run_gui()` function, adding widgets after line ~300:

```python
# Add new control
new_var = tk.StringVar(value="default")
tk.Label(root, text="New Setting:").grid(row=6, column=0)
tk.Entry(root, textvariable=new_var).grid(row=6, column=1)
```

### Adding CLI Arguments

Modify `run_cli()` function, add arguments after line ~480:

```python
parser.add_argument("--new-option", default="value", help="Description")
```

## Troubleshooting

### Common Issues

**Model loading fails:**
- Check GPU/CUDA availability: `torch.cuda.is_available()`
- Verify sufficient RAM/VRAM (model needs ~3GB)
- Try CPU mode if GPU issues persist

**Tags appear in wrong positions:**
- Check `TAG_PATTERN` regex in `SubtitleTranslator`
- Verify placeholder replacement in `restore_tags()`
- Enable debug by adding print statements

**Translation quality issues:**
- Adjust `num_beams` (higher = better quality, slower)
- Adjust `max_length` for longer texts
- Check language codes are correct

**GUI freezes:**
- Verify threading is enabled in `start_translation()`
- Check for blocking operations in main thread

### Debug Workflow

1. Add print statements in relevant functions
2. Check console output for model loading messages
3. Test with small files first
4. Verify file format is supported

## Example Usage Patterns

### Basic Translation

```python
# Create translator
translator = SubtitleTranslator()

# Translate .ass file
output_path, originals, translations = translator.translate_ass_file(
    "input.ass",
    src_lang="en",
    tgt_lang="pl",
    n_tag_idx=5,  # Insert \N at word 5
    progress_callback=print  # Optional progress
)
```

### Batch Processing

```python
# Translate multiple texts
texts = ["Hello", "World", "How are you?"]
translations = translator.translate(
    texts,
    src_lang="en",
    tgt_lang="pl",
    batch_size=8
)
```

### Custom Tag Handling

```python
# Protect custom tags
text = "Custom {tag} here"
protected, tags = translator.protect_tags(text)
# Translate protected text...
restored = translator.restore_tags(translated, tags)
```

## File Structure

```
main.py                 # Complete application (569 lines)
├── SubtitleTranslator  # Translation engine
├── run_gui()           # GUI interface
└── run_cli()           # CLI interface

requirements.txt        # Dependencies (4 packages)
test_translate_ass.py   # Tests
README.md              # User documentation
GUI_LAYOUT.md          # Interface design
```

## Performance Considerations

- **Batch size:** Increase for faster processing (uses more memory)
- **num_beams:** Decrease for faster translation (lower quality)
- **Threading:** Always use for GUI to prevent freezing
- **Model caching:** Model loaded once and reused

## Migration Notes

**From previous version:**
- All functionality from 14 files now in `main.py`
- No separate config files needed
- No complex pipeline stages
- Direct NLLB model usage (no abstraction layers)
- Simplified error handling
- Removed unused post-processing steps

**Breaking changes:**
- No `config.py` - settings now hardcoded or passed as arguments
- No `models.py` - model loading inline
- No complex logging - basic print statements
- No Polish morphology enhancements
- No separate progress controller

## For AI Agents

**When modifying this codebase:**

1. **Everything is in main.py** - Don't look for separate modules
2. **Self-contained design** - No local imports except standard library
3. **Simple is better** - Avoid adding complexity back
4. **Test incrementally** - Run GUI/CLI after each change
5. **Preserve threading** - Keep translation in background thread
6. **Maintain tag handling** - Critical for subtitle formatting
7. **Keep review window** - User expects to verify translations

**Common modifications:**
- Add language: Update `LANG_CODES` dict
- Adjust quality: Modify `generate()` parameters
- New file format: Add `translate_xxx_file()` method
- GUI changes: Edit `run_gui()` function
- CLI options: Edit `run_cli()` parser
