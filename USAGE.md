# Usage Examples

This document provides practical examples for using the NLLB Translation App.

## Single File Translation

### Example 1: English to French
```bash
python translate_ass.py example.ass output_french.ass eng fra
```

**Input (example.ass):**
```
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Hello, how are you today?
```

**Output (output_french.ass):**
```
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Bonjour, comment allez-vous aujourd'hui?
```

### Example 2: Japanese to English
```bash
python translate_ass.py anime.ass anime_english.ass jpn eng
```

### Example 3: Spanish to German
```bash
python translate_ass.py spanish_movie.ass german_movie.ass spa deu
```

## Batch Translation

### Example 1: Translate All Files in a Directory
```bash
# Create input and output directories
mkdir -p input_subs output_subs

# Copy your .ass files to input_subs
cp *.ass input_subs/

# Translate all files from English to French
python batch_translate.py input_subs/ output_subs/ eng fra
```

### Example 2: Selective File Translation
```bash
# Translate only specific files
python batch_translate.py input_subs/ output_subs/ eng spa --pattern "episode*.ass"
```

## Working with Tags

The app automatically preserves .ass formatting tags:

**Input:**
```
Dialogue: 0,0:00:09.00,0:00:13.00,Default,,0,0,0,,{\i1}This is italic{\i0} and this is normal.
```

**Output (English to French):**
```
Dialogue: 0,0:00:09.00,0:00:13.00,Default,,0,0,0,,{\i1}C'est en italique{\i0} et c'est normal.
```

## Tag Types Supported

The app preserves these .ass tags:

- **Italic**: `{\i1}text{\i0}`
- **Bold**: `{\b1}text{\b0}`
- **Underline**: `{\u1}text{\u0}`
- **Strike-out**: `{\s1}text{\s0}`
- **Line breaks**: `\N` or `\n`
- **Hard spaces**: `\h`
- **Colors**: `{\c&HBBGGRR&}text{\r}`
- **Font size**: `{\fs20}text{\r}`
- **Position**: `{\pos(x,y)}text`
- **And many more...**

## Advanced Usage

### Using CPU Instead of GPU
```bash
python translate_ass.py input.ass output.ass eng fra --device cpu
```

### Using Different Model
```bash
# Use a different NLLB model variant (if available)
python translate_ass.py input.ass output.ass eng fra --model facebook/nllb-200-1.3B
```

## Complete Workflow Example

### Scenario: Translating Anime Series

You have episodes 1-12 with English subtitles and want French versions:

```bash
# 1. Organize your files
mkdir -p anime_subs/english anime_subs/french

# 2. Copy English subtitles
cp episode*.ass anime_subs/english/

# 3. Translate all episodes
python batch_translate.py anime_subs/english/ anime_subs/french/ eng fra

# 4. Check results
ls anime_subs/french/
```

### Scenario: Multi-language Translation

Translate to multiple languages:

```bash
# Create output directories
mkdir -p subs/french subs/german subs/spanish

# Translate to French
python batch_translate.py subs/english/ subs/french/ eng fra

# Translate to German
python batch_translate.py subs/english/ subs/german/ eng deu

# Translate to Spanish
python batch_translate.py subs/english/ subs/spanish/ eng spa
```

## Performance Tips

1. **GPU vs CPU**: GPU is 10-30x faster
2. **First Run**: Model download takes 10-30 minutes (one-time only)
3. **Translation Speed**: ~0.5-2 seconds per dialogue line with GPU
4. **Memory**: Ensure 7GB+ GPU memory or use CPU mode
5. **Batch Processing**: More efficient than translating files individually

## Common Issues and Solutions

### Issue: "CUDA out of memory"
**Solution**: Use CPU mode
```bash
python translate_ass.py input.ass output.ass eng fra --device cpu
```

### Issue: Translation quality is poor
**Solution**: 
- Ensure source language is correct
- NLLB works best with complete sentences
- Some language pairs may have limited training data

### Issue: Tags are translated
**Solution**: This shouldn't happen, but if it does:
1. Check your .ass file format is correct
2. Report as a bug with example file

### Issue: Slow translation
**Solution**:
- Use GPU if available
- Close other GPU-intensive applications
- Consider using a smaller model

## Testing Your Installation

Run the included test to verify everything works:

```bash
python test_translate_ass.py
```

Expected output:
```
test_extract_text_from_dialogue ... ok
test_parse_ass_file ... ok
test_protect_and_restore_tags ... ok
test_protect_tags_complex ... ok
test_protect_tags_with_line_breaks ... ok
test_tag_pattern ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.001s

OK
```

## Getting Help

If you encounter issues:

1. Check [INSTALL.md](INSTALL.md) for installation help
2. Read [README.md](README.md) for detailed documentation
3. Run tests to verify installation: `python test_translate_ass.py`
4. Open an issue on GitHub with:
   - Your Python version (`python --version`)
   - Your PyTorch version (`pip show torch`)
   - Error message
   - Example input file (if applicable)
