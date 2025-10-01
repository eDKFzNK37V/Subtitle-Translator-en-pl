# Copilot Instructions for NLLB-3.3B Subtitle Translation App

## Project Overview

- This Python app batch-translates `.ass` subtitle files using Meta's NLLB-200-3.3B model.
- Key files: `translate_ass.py` (core logic), `batch_translate.py` (batch utility), `test_translate_ass.py` (unit tests), `example.ass` (sample input).
- Preserves all formatting, timestamps, and style tags in output files.
- Tag protection: Formatting tags (e.g., `{\i1}`, `\N`) are replaced with placeholders before translation, then restored.
- Language codes are mapped via `ASSTranslator.LANG_CODES` in `translate_ass.py` (e.g., `eng` → `eng_Latn`).

## Developer Workflows

- **Install**: See `INSTALL.md` for Python 3.11+, CUDA, and dependency setup. Use `pip install -r requirements.txt`.
- **Single file translation**: `python translate_ass.py input.ass output.ass eng fra`
- **Batch translation**: `python batch_translate.py input_dir/ output_dir/ eng fra`
- **Testing**: Run `python test_translate_ass.py` (uses mocks, no model download required).
- **Model download**: On first run, the NLLB model (~13GB) is auto-downloaded and cached.
- **CPU/GPU selection**: Use `--device cpu` or `--device cuda` as needed.
- **Pattern matching**: Batch mode supports `--pattern` for file selection (default: `*.ass`).

## Project-Specific Patterns

- **Header preservation**: Subtitle file headers (Script Info, Styles) are never translated or altered.
- **Dialogue parsing**: Only dialogue lines are translated; tags are protected and restored.
- **Error handling**: Scripts exit with clear error messages for missing files, invalid language codes, or empty input.
- **Language extensibility**: To add new languages, update `LANG_CODES` in `translate_ass.py`.
- **Testing conventions**: Tests mock heavy dependencies (torch, transformers) for fast, offline runs.

## Integration & Dependencies

- **Core dependencies**: torch (CUDA 12.1), transformers, sentencepiece, tqdm (see `requirements.txt`).
- **Model**: facebook/nllb-200-3.3B (HuggingFace hub).
- **No web server or API**: All translation is local, file-based.

## Examples

- See `EXAMPLES.md` and `USAGE.md` for input/output samples and advanced usage.
- Example batch command:
  ```bash
  python batch_translate.py input_subs/ output_subs/ eng fra
  ```
- Example test run:
  ```bash
  python test_translate_ass.py
  ```

## File/Directory References

- `translate_ass.py`: Main translation logic, tag handling, language codes
- `batch_translate.py`: Batch processing utility
- `test_translate_ass.py`: Unit tests (mocked)
- `requirements.txt`: Dependency versions
- `example.ass`: Sample subtitle file
- `EXAMPLES.md`, `USAGE.md`: Usage and translation examples
- `INSTALL.md`: Setup and troubleshooting

---

For more, see [README.md](../README.md) and [INSTALL.md](../INSTALL.md).
