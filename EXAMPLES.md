# Translation Examples

This document shows examples of how the translation app processes .ass files.

## Example 1: Simple Dialogue

### Input (English - example.ass)
```
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Hello, how are you today?
Dialogue: 0,0:00:05.00,0:00:08.00,Default,,0,0,0,,I'm doing great, thank you!
```

### Expected Output (French)
```
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Bonjour, comment allez-vous aujourd'hui?
Dialogue: 0,0:00:05.00,0:00:08.00,Default,,0,0,0,,Je vais très bien, merci!
```

**Note**: Timestamps and format are preserved exactly.

---

## Example 2: Formatted Text (with tags)

### Input (English)
```
Dialogue: 0,0:00:09.00,0:00:13.00,Default,,0,0,0,,{\i1}This is italic text{\i0} and this is normal.
```

### Expected Output (French)
```
Dialogue: 0,0:00:09.00,0:00:13.00,Default,,0,0,0,,{\i1}Ceci est du texte en italique{\i0} et ceci est normal.
```

**Note**: The `{\i1}` and `{\i0}` tags remain unchanged and in the correct positions.

---

## Example 3: Line Breaks

### Input (English)
```
Dialogue: 0,0:00:14.00,0:00:18.00,Default,,0,0,0,,{\b1}Bold text{\b0}\Nwith a line break.
```

### Expected Output (French)
```
Dialogue: 0,0:00:14.00,0:00:18.00,Default,,0,0,0,,{\b1}Texte en gras{\b0}\Navec un saut de ligne.
```

**Note**: The `\N` line break tag is preserved in its original position.

---

## Example 4: Complex Formatting

### Input (English)
```
Dialogue: 0,0:00:19.00,0:00:23.00,Default,,0,0,0,,{\c&HFF0000&}Colored text{\r} back to normal.
```

### Expected Output (French)
```
Dialogue: 0,0:00:19.00,0:00:23.00,Default,,0,0,0,,{\c&HFF0000&}Texte coloré{\r} retour à la normale.
```

**Note**: Color tags `{\c&HFF0000&}` and reset tag `{\r}` are preserved.

---

## Example 5: Header Preservation

The .ass file header (Script Info, Styles, etc.) is **never** translated:

### Input Header
```
[Script Info]
Title: Example Subtitle
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, ...
Style: Default,Arial,48,&H00FFFFFF,...
```

### Output Header
```
[Script Info]
Title: Example Subtitle
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, ...
Style: Default,Arial,48,&H00FFFFFF,...
```

**Note**: Header remains identical, ensuring subtitle file compatibility.

---

## How It Works

The translation process follows these steps:

1. **Parse**: Separate header from dialogue lines
2. **Extract**: Get text from each dialogue line
3. **Protect**: Replace tags with placeholders (e.g., `{\i1}` → `<TAG0>`)
4. **Translate**: Send protected text to NLLB model
5. **Restore**: Replace placeholders with original tags
6. **Rebuild**: Combine timestamp + translated text
7. **Save**: Write header + translated dialogues to output file

---

## Testing the Translation

To test with the included example file:

```bash
# This command would translate example.ass from English to French
python translate_ass.py example.ass example_fr.ass eng fra
```

The output file `example_fr.ass` will:
- Have the same structure as the input
- Preserve all timestamps
- Keep all formatting tags
- Contain French translations of the dialogue text

---

## Quality Expectations

### High Quality Translation For:
- Common language pairs (eng→fra, eng→spa, jpn→eng, etc.)
- Complete sentences
- Standard dialogue
- Technical terms (generally preserved)

### May Need Review For:
- Rare language pairs
- Idiomatic expressions
- Cultural references
- Puns and wordplay
- Names (may be transliterated)

### Always Preserved:
- All timestamps
- All style tags
- All formatting
- File structure
- Subtitle synchronization

---

## Actual Translation Output

To see actual translations from the NLLB model, you would need to:

1. Install the dependencies: `pip install -r requirements.txt`
2. Run the translator: `python translate_ass.py example.ass output.ass eng fra`
3. Compare input and output files

The examples above show the expected behavior and format. The actual translation quality depends on the NLLB model's training for your specific language pair.
