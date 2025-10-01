# Subtitle Translator (NLLB)

A simplified, self-contained subtitle translator using Facebook's NLLB-3.3B model.

## Features

- **Single file application** - All code in one main.py file (569 lines)
- **GUI and CLI** - Both interfaces in one place
- **Multi-format support** - Translate .ass, .srt, and .txt files
- **Tag preservation** - Automatically protects subtitle formatting tags
- **\N tag insertion** - Control line breaks in subtitles
- **Translation review** - Edit translations before saving
- **Threading** - Non-blocking GUI during translation
- **Minimal dependencies** - Only 4 core packages needed

## Installation

### 1. Install Python 3.8+

### 2. Install dependencies

For CUDA GPU support:
```bash
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

For CPU only:
```bash
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

## Usage

### GUI Mode (Default)

Simply run:
```bash
python main.py
```

The GUI provides:
- File browser for subtitle selection
- Source and target language selection
- File type selection (.ass, .srt, .txt)
- \N tag word index control (for .ass files)
- Progress tracking
- Translation review window

### CLI Mode

```bash
python main.py <input_file> [options]
```

**Options:**
- `--src LANG` - Source language code (default: en)
- `--tgt LANG` - Target language code (default: pl)
- `--nwordix N` - Word index for \N tag insertion (default: 0=auto, .ass only)
- `--batch-size N` - Batch size for translation (default: 8)

**Examples:**
```bash
# Basic translation
python main.py subtitle.ass --src en --tgt pl

# Custom \N tag insertion
python main.py subtitle.ass --nwordix 5

# Translate SRT file
python main.py subtitle.srt --src en --tgt ja

# Translate text file
python main.py document.txt --src en --tgt fr
```

## Supported Languages

- English (en)
- Polish (pl)
- Japanese (ja)
- French (fr)
- German (de)

More languages can be added by extending the `LANG_CODES` dictionary in main.py.

## File Format Support

### .ass (Advanced SubStation Alpha)
- Preserves all formatting tags (e.g., `{\pos(x,y)}`, `{\an8}`)
- Supports \N tag insertion for line breaks
- Maintains dialogue structure and timing

### .srt (SubRip)
- Preserves timing information
- Maintains subtitle numbering
- Supports basic formatting

### .txt (Plain Text)
- Translates non-empty lines
- Preserves whitespace and formatting
- Maintains line structure

## Architecture

The application consists of a single `main.py` file with three main components:

1. **SubtitleTranslator Class** - Core translation engine
   - NLLB model loading and management
   - Tag protection/restoration
   - \N tag insertion logic
   - File format handlers

2. **GUI Function** - Tkinter-based interface
   - File browser
   - Language selection
   - Progress tracking
   - Translation review window
   - Threading for non-blocking operation

3. **CLI Function** - Command-line interface
   - Argument parsing
   - Progress display
   - Batch processing

## Development

### File Structure
```
main.py                 # Complete application (569 lines)
requirements.txt        # Dependencies
test_translate_ass.py   # Tests
README.md              # This file
```

### Code Overview

**Translation Flow:**
1. Load subtitle file
2. Extract text and tags
3. Protect tags with placeholders
4. Translate text using NLLB model
5. Restore tags from placeholders
6. Insert \N tags (for .ass files)
7. Save translated file

**GUI Flow:**
1. User selects file and settings
2. Translation runs in background thread
3. Progress updates in main thread
4. Review window shows results
5. User can edit before final save

## Changelog

### Version 2.0 (Current)
- Complete rewrite as single-file application
- Reduced from 4,216 to 569 lines (87% reduction)
- Removed 14 files, kept only main.py
- Added .srt and .txt support
- Simplified dependencies to 4 packages
- Improved threading and progress tracking
- Added translation review window

### Version 1.0 (Previous)
- Multi-file architecture (13 Python files)
- Complex pipeline with multiple stages
- Many unused features and dependencies
- Limited to .ass files

## License

[Add your license here]

## Credits

- Facebook AI Research for NLLB model
- HuggingFace for Transformers library
