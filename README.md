`Keep in mind that this project was made entirely for fun and to test capabilities of LLMs and Visual Studio Code editor. (Don't use it for professional purposes because I cannot guarantee you the correctness of the translation.)`

# Subtitle Translator (English ↔ Polish, etc.)

A unified, easy-to-use subtitle translation tool supporting `.ass`, `.srt`, and `.txt` formats. Powered by NLLB models (Meta AI) with optional LoRA adapter support for custom fine-tuned models. Includes both a GUI and CLI.It's suited for Polish language.

---

## Features

- **Batch translation** with NLLB-200 (1.3B/3.3B) or your own LoRA adapters
- **⚡ 10× faster** with optimizations: FP16, quantization, adaptive batching
- **GUI** (Tkinter) and **CLI** modes
- **Speakers grouping** for `.ass` files(should improve the context translation for dialogues)
- **Subtitle tag protection** and restoration
- **No file overwrite**: output files are auto-incremented if a name conflict exists
- **Customizable batch size, beam search, and \N tag insertion**
- **Translation log** for every run(which includes things like: how much time it took;how many lines were translated; comparasion originals ---> translated; device and operation time)
---

## Chapters

- [Installation](#installation)
- [Quick Start](#quick-start)
- [GUI Layout](#gui-layout)
- [Usage Examples](#usage-examples)
- [File format & Tag handling](#file-formats-and-tag-handling)
- [Examples (input → expected output)](#examples-input--expected-output)
- [Performance & Optimizations](#performance--optimizations)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)
- [Developer notes](#developer-notes)

---

## Installation

System requirements

- Python: 3.11 or higher
- OS: Linux, Windows or macOS
- GPU (recommended): NVIDIA GPU with CUDA 12.1 support
- VRAM: At least 4GB (+12GB recommended)
- RAM: At least 8GB (16GB recommended)
- Disk space: ~25GB for model and dependencies

Step-by-step

1. **Clone the repository:**

```bash
git clone https://github.com/eDKFzNK37V/NLLB-3.3-test.git
cd NLLB-3.3-test
```

2. Install Python 3.11+ (use your platform's package manager or download from python.org).
3. (Optional) Create and activate a virtual environment:

```bash
python3.11 -m venv venv
source venv/bin/activate
```

4. Install dependencies:

- GPU (recommended):

```bash
pip install -r requirements.txt
```

- CPU-only (if you don't have device with CUDA cores (NVIDIA cards):

```bash
pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu
pip install transformers sentencepiece protobuf tqdm
```

Notes on model download: On first run the NLLB model will be downloaded automatically and may take a while (several minutes to tens of minutes depending on internet speed).

### Windows quick install

1. Ensure Python is installed (see steps above).
2. Run `install.bat` to create the `.venv` and install dependencies.
3. Run `run.bat` to launch the app.

- [Chapters](#chapters)

---

## Quick Start

GUI mode (default):

```bash
python subtitle_translator.py
```

CLI mode:

```bash
python subtitle_translator.py input.ass --src en --tgt pl
```

Common CLI flags:

`--device cpu` — force CPU mode
`--model <model-name>` — use a specific model (e.g., `facebook/nllb-200-distilled-1.3B`)
`--batch-size N` — set batch size (default optimized to 32)
`--fp16` / `--no-fp16` — enable/disable FP16
`--quantize --quantize-bits 4` — enable quantization (requires bitsandbytes)
`--num-beams N` — set beam search width (higher = better quality, slower; default: 4)
`--enable-grouping` — group consecutive dialogue lines by speaker (for .ass files, ONLY if the dialogues have name metadata in it; default: off)

- [Chapters](#chapters)

---

## GUI Layout

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Subtitle Translator (NLLB)                                       [_][□][X] │
├────────────────────────────────────────────────────────────────────────────┤
│ File Selection                                                             │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ File:           [______________________________] [Browse]              │ │
│ │ LoRA Adapter:   [______________________________] [Browse]              │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│ Translation Settings                                                       │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ Source: [en ▼]  Target: [pl ▼]  Format: [ass ▼]                        │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│ Advanced Options                                                           │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ \N index: [ 0 ]  Batch: [32]  Beams: [4]                               │ │
│ │ [ ] Group by speaker (.ass only)                                       │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│ Performance Optimizations                                                  │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ [x] FP16 (half precision)  [ ] Quantization  Bits: [4 ▼]               │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│                          Translation: 0%                                   │
│                               Ready                                        │
│                                                                            │
│                       [ Start Translation ]                                │
└────────────────────────────────────────────────────────────────────────────┘
```

**Widget/Control Groups:**

- **File Selection:**
  - File path entry + Browse button
  - LoRA Adapter path entry + Browse button
- **Translation Settings:**
  - Source language dropdown (en, pl, ja, fr, de)
  - Target language dropdown (en, pl, ja, fr, de)
  - Format dropdown (ass, srt, txt)
- **Advanced Options:**
  - \N index spinbox (0–50)
  - Batch size spinbox (1–64)
  - Beams spinbox (1–10)
  - [ ] Group by speaker (.ass only) checkbox
- **Performance Optimizations:**
  - [x] FP16 (half precision) checkbox
  - [ ] Quantization checkbox
  - Bits dropdown (4, 8)
- **Progress/Status:**
  - Progress label (e.g., Translation: 0%)
  - Status label (e.g., Ready, Loading model, Translating, Complete)
- **Action:**
  - [ Start Translation ] button

The GUI runs translation in a background thread to avoid freezing. After translation, a review window appears for manual edits before saving.

- [Chapters](#chapters)

---

## Usage Examples

Single file translation:

```bash
python subtitle_translator.py input.ass --src en --tgt fr
```

Batch translation (example):

```bash
for f in input_subs/*.ass; do python subtitle_translator.py "$f" --src en --tgt fr; done
```

Advanced examples:

- CPU mode:

```bash
python subtitle_translator.py input.ass --src en --tgt fr --device cpu
```

- Different model:

```bash
python subtitle_translator.py input.ass --src en --tgt fr --model facebook/nllb-200-1.3B
```

---

## File formats and tag handling

Supported input types:

- `.ass` (Advanced SubStation Alpha)
- `.srt` (SubRip)
- `.txt` (plain text)

Key behaviors:

- `.ass` headers (Script Info, Styles, etc.) are preserved and not translated.
- Dialogue lines are parsed and only the dialogue text is sent to the translator.
- Formatting tags (ASS tags like `{\b1}`, `{\i1}`, `{\pos(x,y)}`) are protected by placeholders during translation and restored afterward.
- Line breaks: `\N` and `\n` are preserved.
- Plain text: empty or purely numeric lines are skipped.

Tag protect/restore pattern (example):

- Before translation: "Hello {\pos(320,240)} world" → protected: "Hello <TAG0> world"
- After translation: "Bonjour <TAG0> monde" → restored: "Bonjour {\pos(320,240)} monde"
- [Chapters](#chapters)

---

## Examples (input → expected output)

Example 1: Simple dialogue

Input (english):

```
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Hello, how are you today?
Dialogue: 0,0:00:05.00,0:00:08.00,Default,,0,0,0,,I'm doing great, thank you!
```

Expected output (French):

```
Dialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Bonjour, comment allez-vous aujourd'hui?
Dialogue: 0,0:00:05.00,0:00:08.00,Default,,0,0,0,,Je vais très bien, merci!
```

Example 2: Formatted text (italics preserved)

Input:

```
Dialogue: 0,0:00:09.00,0:00:13.00,Default,,0,0,0,,{\i1}This is italic text{\i0} and this is normal.
```

Expected output (French):

```
Dialogue: 0,0:00:09.00,0:00:13.00,Default,,0,0,0,,{\i1}Ceci est du texte en italique{\i0} et ceci est normal.
```

Example 3: Line breaks

Input:

```
Dialogue: 0,0:00:14.00,0:00:18.00,Default,,0,0,0,,{\b1}Bold text{\b0}\Nwith a line break.
```

Expected output (French):

```
Dialogue: 0,0:00:14.00,0:00:18.00,Default,,0,0,0,,{\b1}Texte en gras{\b0}\Navec un saut de ligne.
```

Header preservation: The .ass header must remain identical between input and output to maintain compatibility.

- [Chapters](#chapters)

---

## Performance & Optimizations

### Overview of Optimizations

| Optimization              | Expected speedup  | Description                                       |
| ------------------------- | ----------------- | ------------------------------------------------- |
| Batch size 32             | ×3–4              | Increased from 8 to 32 with adaptive OOM handling |
| FP16 mode                 | ×1.5              | Half precision inference on GPU                   |
| Quantized model           | ×2–3              | 4-bit or 8-bit quantization                       |
| Tokenization improvements | ×1.2              | Use max_new_tokens and optimized encoding         |
| Combined total            | **10× or better** | All optimizations work together                   |

### Expected Speedup by Optimization

| Optimization                | Individual Speedup | Cumulative Speedup |
| --------------------------- | ------------------ | ------------------ |
| Baseline (FP32, batch=8)    | 1.0×               | 1.0×               |
| Batch size 32               | 3-4×               | 3-4×               |
| + FP16 mode                 | 1.5×               | 4.5-6×             |
| + TF32 (Ampere+ GPU)        | 1.2×               | 5.4-7.2×           |
| + Tokenization fixes        | 1.1×               | 6-8×               |
| **OR Quantization (4-bit)** | **2-3× vs FP16**   | **9-12×**          |

### Real-World Performance Estimate

For a 300-line .ass subtitle file (EN→PL translation):

| Configuration                  | Estimated Time  | Speedup |
| ------------------------------ | --------------- | ------- |
| Original (batch=8, FP32)       | ~180 seconds    | 1.0×    |
| Batch=32 only                  | ~60 seconds     | 3.0×    |
| Batch=32 + FP16                | ~40 seconds     | 4.5×    |
| Batch=32 + FP16 + TF32         | ~33 seconds     | 5.5×    |
| Batch=32 + 4-bit Quantization  | ~20 seconds     | 9.0×    |
| **All optimizations combined** | **~18 seconds** | **10×** |

_Note: Actual results depend on GPU model, text complexity, and system configuration._

### Memory Savings

GPU memory usage for `facebook/nllb-200-3.3B` model:

| Configuration      | VRAM Required | Savings |
| ------------------ | ------------- | ------- |
| FP32 (original)    | ~13 GB        | -       |
| FP16               | ~7 GB         | 46%     |
| 8-bit quantization | ~4 GB         | 69%     |
| 4-bit quantization | ~2.5 GB       | 81%     |

### Feature Compatibility

| Feature        | FP32 | FP16 | 4-bit Quant | 8-bit Quant |
| -------------- | ---- | ---- | ----------- | ----------- |
| GUI            | ✓    | ✓   | ✓           | ✓           |
| CLI            | ✓    | ✓   | ✓           | ✓           |
| LoRA adapters  | ✓    | ✓   | ✓           | ✓           |
| All file types | ✓    | ✓   | ✓           | ✓           |
| CPU only       | ✓    | ✗   | ✗           | ✗           |
| Adaptive batch | ✓    | ✓   | ✓           | ✓           |

### Default Behavior Changes

| Setting      | Old Default | New Default | Reason               |
| ------------ | ----------- | ----------- | -------------------- |
| Batch size   | 8           | 32          | 3-4× faster          |
| FP16 mode    | Off         | On (GPU)    | 1.5× faster, free    |
| Quantization | N/A         | Off         | Opt-in for max speed |

- Polish targets use a higher `max_new_tokens` limit (150) to reduce truncation from morphological expansion.

- [Chapters](#chapters)

### CLI examples

```bash
# Maximum speed with 4-bit quantization
python subtitle_translator.py input.ass --src en --tgt pl --quantize --quantize-bits 4

# Balanced: FP16 and larger batch
python subtitle_translator.py input.ass --src en --tgt pl --fp16 --batch-size 32
```

_Memory and compatibility notes:_

- FP16 requires CUDA GPU. Not valid on CPU.
- Quantization requires `bitsandbytes` and CUDA GPU.
- Adaptive batch sizing will reduce batch size on OOM errors automatically.
- [Chapters](#chapters)

---

## Troubleshooting

Common issues and fixes:

- "No module named 'torch'" → run `pip install -r requirements.txt`
- CUDA version mismatch → check `nvidia-smi` and install matching PyTorch wheels
- Out of memory → enable quantization, reduce batch size, or use CPU mode
- Slow translation on CPU → consider using GPU or a smaller model
- Tags translated into output → ensure input file is a valid .ass and tags match supported patterns

- If you encounter a problem that is not described there or is not suited for your platform, pm me or create an issue.

- [Chapters](#chapters)

---

## Testing

Run the repository tests to verify tag protection/restore and other functionality:

```bash
python test_translate_ass.py
```

Expected minimal test output (example):

```
Ran 6 tests
OK
```

There are also optimization tests `test_optimizations.py` described in the performance docs.

- [Chapters](#chapters)

---

## Developer notes

- Everything core lives in `subtitle_translator.py`.
- Key public entrypoints: the `SubtitleTranslator` class, `run_gui()` and `run_cli()`.
- Add new languages by editing `LANG_CODES` mapping in the translator class.
- Adjust translation parameters in `translate()` (beam size, max tokens).
- GUI is threaded: keep long-running ops off the main thread.

- [Chapters](#chapters)

---

---

End of documentation.
