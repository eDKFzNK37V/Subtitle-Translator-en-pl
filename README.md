# NLLB-3.3B Translation App for .ass Subtitle Files

A Python application that translates .ass (Advanced SubStation Alpha) subtitle files using Facebook Meta's NLLB-200-3.3B model. The app preserves formatting, timestamps, and styling tags while providing high-quality neural machine translation.

## Features

- 🌍 Supports 200+ languages via NLLB-200-3.3B model
- 📝 Preserves .ass file formatting and structure
- 🏷️ Avoids translating style tags and control sequences
- ⏱️ Maintains timestamps and synchronization
- 💬 Optimized for dialogue translation
- 🚀 CUDA acceleration support
- 🎯 Handles complex .ass formatting (bold, italic, colors, line breaks)

## Requirements

- Python 3.11+
- CUDA 12.1 (for GPU acceleration)
- ~13GB disk space for the NLLB-3.3B model
- ~7GB GPU memory (recommended)

## Installation

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

**Quick Start:**
```bash
git clone https://github.com/eDKFzNK37V/NLLB-3.3-test.git
cd NLLB-3.3-test
pip install -r requirements.txt
```

## Usage

For detailed usage examples and scenarios, see [USAGE.md](USAGE.md).

For translation examples showing input/output, see [EXAMPLES.md](EXAMPLES.md).

### Basic Usage

```bash
python translate_ass.py input.ass output.ass <source_lang> <target_lang>
```

### Examples

**Translate from English to French:**
```bash
python translate_ass.py example.ass output_french.ass eng fra
```

**Translate from Japanese to English:**
```bash
python translate_ass.py japanese_subs.ass english_subs.ass jpn eng
```

**Translate from Spanish to German:**
```bash
python translate_ass.py spanish.ass german.ass spa deu
```

### Command-Line Options

```
positional arguments:
  input                 Input .ass file path
  output                Output .ass file path
  src_lang             Source language code (e.g., eng, jpn, fra)
  tgt_lang             Target language code (e.g., eng, fra, spa)

optional arguments:
  -h, --help           Show help message
  --model MODEL        Model name (default: facebook/nllb-200-3.3B)
  --device {cuda,cpu}  Device to use (default: auto-detect)
```

### Supported Languages

Common language codes (3-letter):

| Code | Language | Code | Language | Code | Language |
|------|----------|------|----------|------|----------|
| eng | English | fra | French | deu | German |
| spa | Spanish | ita | Italian | jpn | Japanese |
| kor | Korean | zho | Chinese | rus | Russian |
| ara | Arabic | por | Portuguese | nld | Dutch |
| pol | Polish | tur | Turkish | hin | Hindi |
| vie | Vietnamese | tha | Thai | ind | Indonesian |

The NLLB model supports 200+ languages. The above are pre-configured, but you can add more by editing the `LANG_CODES` dictionary in `translate_ass.py`.

## How It Works

1. **File Parsing**: The app parses the .ass file, separating header information from dialogue lines.

2. **Tag Protection**: Style tags (like `{\i1}`, `{\b1}`, `\N`, etc.) are temporarily replaced with placeholders to prevent translation.

3. **Translation**: Text is translated using the NLLB-200-3.3B model with beam search for high-quality results.

4. **Tag Restoration**: Original tags are restored to their positions in the translated text.

5. **File Output**: The translated dialogues are combined with the original header to create a properly formatted .ass file.

## Example .ass File

An example subtitle file (`example.ass`) is included in the repository. It demonstrates various .ass features:
- Basic dialogues
- Italic text formatting
- Bold text formatting
- Line breaks
- Colored text

You can use it to test the translation:
```bash
python translate_ass.py example.ass example_translated.ass eng fra
```

### Batch Translation

Translate multiple files at once:

```bash
python batch_translate.py input_folder/ output_folder/ eng fra
```

This will translate all .ass files in the input folder and save them to the output folder.

## Technical Details

### Dependencies

- **PyTorch 2.5.1 (CUDA 12.1)**: Deep learning framework
- **Transformers**: HuggingFace library for NLLB model
- **SentencePiece**: Tokenization
- **tqdm**: Progress bars

### Model Information

- **Model**: facebook/nllb-200-3.3B
- **Type**: Multilingual sequence-to-sequence transformer
- **Parameters**: 3.3 billion
- **Languages**: 200+
- **Use Case**: High-quality neural machine translation

### Performance

- First run will download the ~13GB model (cached for future use)
- Translation speed depends on:
  - GPU availability (CUDA highly recommended)
  - Text length
  - Number of dialogue lines
- Typical speed: ~0.5-2 seconds per dialogue line with GPU

## Troubleshooting

### CUDA Out of Memory

If you encounter CUDA out of memory errors:
1. Reduce batch size (the app processes one line at a time by default)
2. Use CPU mode: `--device cpu`
3. Use a smaller model variant if available

### Model Download Issues

The model will be automatically downloaded on first use. If download fails:
1. Check internet connection
2. Ensure sufficient disk space (~13GB)
3. Try downloading manually from HuggingFace

### Import Errors

If you get import errors:
```bash
pip install --upgrade -r requirements.txt
```

## License

This project uses the NLLB-200 model which is licensed under CC-BY-NC 4.0.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

- Facebook AI Research for the NLLB model
- HuggingFace for the Transformers library