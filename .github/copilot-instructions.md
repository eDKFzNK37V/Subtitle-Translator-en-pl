# Copilot Instructions for Subtitle-Translator-en-pl

## Project Overview

- **Purpose:** Translate and correct subtitle files between English and Polish, supporting `.ass`, `.srt`, and `.txt` formats. Focus on robust tag handling, context-aware dialogue grouping, neural and rule-based correction, and user-driven translation workflows.
- **Entry Points:**
  - `main.py` (CLI), `main_gui.py` (GUI)
  - GUI logic: `gui.py`, `gui_m2m100.py`, `gui_nllb.py`
  - Core pipeline: `subtitle_workflow.py` (translation/correction logic, tag handling)
  - Utilities: `text_tools.py` (tag utils, dialogue grouping), `grammar.py`, `logs.py`, `resources.py`, `config.py`

## Architecture & Data Flow

- **Pipeline:**
  1. Load subtitle file (`subtitle_workflow.py`)
  2. Preprocess: extract all `\N` tags (see `text_tools.py: extract_newline_tags`), restore tag placeholders (see below), optionally grammar-check (`grammar.py`)
  3. Dialogue grouping: group consecutive lines for translation if the next starts with a lowercase letter, but preserve idioms and context (see `text_tools.py: group_dialogue_lines`).
  4. Translate using selected model (`subtitle_workflow.py`, `models.py`)
  5. Post-process:
     - Restore tags and placeholders (see `text_tools.py: extract_tags_with_placeholders`, `restore_tags_from_placeholders`).
     - Neural grammar correction (T5-based, see `text_tools.py: correct_grammar[_batch]`), then LanguageTool correction (`grammar.py`).
     - Glossary/consistency check (planned: see `resources.py` for static terms).
     - Style/tone adjustment (planned: see `text_tools.py` for hooks).
     - Context-aware `\N` reinsertion: use punctuation/clause boundaries, not just word index (see `insert_newline_tags_at_wordidx`).
     - Confidence-based fallback: if correction is low-confidence, revert to original translation.
     - Save output.
- **GUI:**
  - Built with `tkinter` (`gui.py`, `gui_m2m100.py`, `gui_nllb.py`)
  - Model selection, progress, and user-configurable `\N` reinsertion index (Spinbox)
- **Batch/Context-Aware Processing:**
  - `pipeline.py` provides batch correction and context-aware translation, always calling into `subtitle_workflow.py`

## Developer Workflows

- **Run GUI:**
  - `python main_gui.py` or `run_main.bat` (Windows)
- **Run CLI:**
  - `python main.py <input_file>`
- **Environment:**
  - Use the `subtitle-env` virtual environment: `subtitle-env\Scripts\activate` (PowerShell)
  - Dependencies: `requirements.txt`
- **Testing:**
  - No formal test suite; validate by running translation on sample files

## Project-Specific Patterns

- **Tag Handling & Placeholders:**
  - All `\N` tags are removed before translation and reinserted after post-processing. Tag placeholders are extracted and restored using `extract_tags_with_placeholders` and `restore_tags_from_placeholders` in `text_tools.py`. Always preserve original tag formatting (e.g., `{\pos(320,243.333)}`) and spacing.
- **Context-Aware `\N` Reinsertion:**
  - Use `insert_newline_tags_at_wordidx` in `text_tools.py`, but prefer punctuation/clause boundaries for natural line breaks. Consider user preview/override in GUI.
- **Dialogue Grouping:**
  - Use `group_dialogue_lines` and `split_grouped_translations` in `text_tools.py`. Group only when context/idiom is preserved; avoid breaking up idiomatic or multi-line expressions.
- **Neural Grammar Correction:**
  - Use `correct_grammar`/`correct_grammar_batch` (T5-based) before LanguageTool. Fine-tune on subtitle data for best results. See `text_tools.py` and `grammar.py`.
- **Glossary/Consistency:**
  - Use static glossary in `resources.py` (planned) to enforce consistent translation of key terms (e.g., "leader", "raid").
- **Style/Tone Adjustment:**
  - Add post-processing hooks in `text_tools.py` to adjust register/tone for subtitles (planned: see comments for extension points).
- **Correction Fallback:**
  - If neural or rule-based correction is low-confidence, revert to original translation. Use confidence scores from `correct_grammar` or LanguageTool.
- **Model Integration:**
  - Model-specific GUIs: `gui_m2m100.py`, `gui_nllb.py`. All models managed in `models.py`. Language code mapping is model-specific (see `get_model_lang_code` in `subtitle_workflow.py`).
- **Cross-Component Patterns:**
  - Both GUI and CLI use the same translation pipeline in `subtitle_workflow.py`. Logging via `logs.py`. Avoid circular imports by importing GUI entry points only inside functions.
- **Configuration:**
  - Centralized in `config.py`.
- **Resource Management:**
  - Static resources and language files in `resources.py`.

## External Dependencies

- **HuggingFace Transformers** for translation models
- **Tkinter** for GUI
- **pysubs2** for subtitle parsing
- **CUDA** support is optional (`CUDA-TEST.py`)

## Conventions & Examples

- **File Naming:** GUI files prefixed with `gui_`, model logic in `models.py`, pipeline in `pipeline.py`.
- **Error Handling:** Most errors are logged, not raised to the user.
- **To translate a subtitle:** `python main.py example.srt`.
- **To launch the GUI:** `python main_gui.py`.
- **Tag/\N Example:**
  - Input: `Hello,\Nworld!`
  - After extraction: `Hello, world!` (with tag count)
  - After translation/correction: `Cześć, świecie!`
  - After context-aware reinsertion: `Cześć,\Nświecie!`

## Troubleshooting

- For model/language code errors, see `subtitle_workflow.py` and ensure correct mapping for the selected model.
- For tag placement issues, check that all `\N` and tag handling is done via `text_tools.py` utilities and is called after all post-processing.
- For dialogue grouping/fragmentation, review `group_dialogue_lines` and ensure idioms/context are preserved.
- For correction quality, check neural model confidence and fallback logic in `text_tools.py` and `grammar.py`.
- Refer to `README.md` and code comments for further usage and architecture details.
