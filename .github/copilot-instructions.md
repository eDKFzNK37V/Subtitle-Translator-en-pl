# Subtitle-Translator-en-pl: Copilot AI Agent Guide

## Architecture & Data Flow

- **Entry point:** `main.py` (runs GUI by default)
- **GUI logic:** `gui.py` (Tkinter-based, all user interaction and progress callbacks)
- **Core pipeline:** `subtitle_workflow.py` (orchestrates translation, correction, tag handling)
- **Translation/correction:** `translate.py`, `pipeline.py`, `text_tools.py` (batch translation, grammar, punctuation, tag extraction/restoration)
- **Model loading:** `models.py` (HuggingFace Transformers, PyTorch)
- **Subtitle I/O:** `utils.py` (encoding detection, subtitle/text read/write)
- **Logging:** `logs.py` (per-line and summary logs, diff/diacritics tracking)

**Data Flow:**

1. Load subtitle/text lines (`utils.py:load_subtitle_lines`)
2. Preprocess: extract tags (`text_tools.py:extract_tags`), remove/restore formatting
3. Translate/correct in batch (`translate.py:translate_batch`, `pipeline.py:correct_text_batch`)
4. Restore tags, reformat, and save (`utils.py:save_subtitle_lines`)
5. Log changes (`logs.py:SubtitleLogger`)

## Developer Workflows

- **Run GUI:** `python main.py` or `run_main.bat`
- **Activate env:** `subtitle-env\Scripts\activate` (PowerShell)
- **Install deps:** `pip install -r requirements.txt` (install torch separately for CUDA/CPU)
- **Test translation logic:** `python test_translate_ass.py` (if present)
- **Debug pipeline:** Add print/logs in `subtitle_workflow.py`, `gui.py`, or `logs.py`

## Project-Specific Patterns & Conventions

- **Tag handling:** Always extract tags (e.g., `{\pos(320,240)}`) before translation, restore after. See `text_tools.py:extract_tags`, `restore_tags`.
- **Formatting preservation:** For `.txt` files, preserve leading/trailing whitespace and newlines (see `gui.py:review_txt_translations`).
- **Batch processing:** All translation/correction is done in batches for speed and context (see `translate.py:translate_batch`, `pipeline.py:correct_text_batch`).
- **Logging:** Use `logs.py:SubtitleLogger` for per-line and summary logs, including word diffs and diacritics.
- **Model/device config:** All models use `config.py:DEVICE` for CPU/GPU selection.
- **Supported formats:** `.ass`, `.srt`, `.txt` only (see `utils.py:load_subtitle_lines`).

## Integration & Dependencies

- HuggingFace Transformers (translation, grammar, punctuation)
- PyTorch (neural models)
- LanguageTool Python (grammar correction)
- pysubs2 (subtitle parsing)
- Tkinter (GUI)

## Example Usage

- Translate: `python main.py example.srt`
- GUI: `python main.py` or `run_main.bat`
- Tag handling:
  - Input: `Hello,\Nworld! {\pos(320,240)}`
  - After extraction: `Hello, world!`
  - After translation: `Cześć, świecie!`
  - After reinsertion: `Cześć,\Nświecie! {\pos(320,240)}`

## Troubleshooting

- Model/language errors: see `subtitle_workflow.py`, `models.py`
- Tag/formatting issues: see `text_tools.py`, `gui.py`
- Logging: see `logs.py`
- Encoding: see `utils.py:_detect_encoding`
- For more, see `README.md` and code comments
