## Project-Specific Conventions & Integration Points

- **Tag Handling:**

  - Always extract and remove `\N` and all subtitle tags before translation (see `text_tools.py: extract_newline_tags`, `extract_tags_with_placeholders`).
  - Restore tags after translation using `restore_tags_from_placeholders` to preserve original formatting and timing.
  - Tag placeholders are used to ensure tags are reinserted at the correct semantic position, not just at the start/end of lines.

- **Dialogue Grouping:**

  - Use `group_dialogue_lines` to combine up to 3 consecutive lines for context-aware translation (idiom/context detection).
  - After translation, split grouped results back to original lines with `split_grouped_translations`.

- **Model Selection:**

  - All model/device logic is centralized in `models.py` and `config.py`.
  - Use `get_nllb_globals()` for loading the NLLB model and tokenizer; language code mapping is handled in `subtitle_workflow.py:get_model_lang_code`.
  - Torch device selection is automatic (CUDA if available, else CPU).

- **Correction & Glossary:**

  - Use `correct_grammar_with_fallback` for grammar correction (confidence threshold ≥0.6, fallback to original if low confidence).
  - Glossary is applied pre-translation and contextually using `apply_glossary(text, use_context=True)` (see `resources.py`).

- **Logging & Progress:**

  - All CLI/GUI events, corrections, and progress are logged via `logs.py` and `progress_controller.py`.
  - Correction logs and session summaries are written for traceability and debugging.

- **Batch/Context-Aware Processing:**

  - All translation and correction is performed in batches for efficiency and context preservation (see `pipeline.py`, `subtitle_workflow.py`).
  - Correction and translation pipelines are designed to minimize over-correction and preserve original meaning.

- **GUI/CLI Integration:**

  - Both GUI and CLI workflows use the same core pipeline and utilities, ensuring consistent results.
  - GUI logic is in `gui.py`, `gui_nllb.py`, and `progress_controller.py`.

- **Testing & Extensibility:**
  - Test core logic with `python test_core_functions.py` (if present).
  - All new features should integrate with logging, tag handling, and batch/context-aware patterns.

# Subtitle-Translator-en-pl: Copilot AI Agent Guide

## Architecture & Data Flow

- **CLI entry:** `main.py` (also launches GUI if no file provided)
- **GUI entry:** `main_gui.py` → `gui.py`, `gui_nllb.py`, `gui_m2m100.py`
- **Core pipeline:** `subtitle_workflow.py` (translation, correction, tag handling)
- **Batch/context-aware processing:** `pipeline.py` (calls `subtitle_workflow.py`)
- **Utilities:** `text_tools.py` (tag utils, dialogue grouping), `logs.py`, `resources.py`, `config.py`, `utils.py`

**Data Flow:**

1. Load subtitle (`subtitle_workflow.py`)
2. Preprocess: extract `\N` tags (`text_tools.py: extract_newline_tags`), extract tag placeholders (`extract_tags_with_placeholders`)
3. Group dialogue lines (`group_dialogue_lines`)
4. Translate (model via `models.py`, glossary via `resources.py`)
5. Post-process: restore tags (`restore_tags_from_placeholders`), grammar correction (`correct_grammar_with_fallback`), style/tone (`adjust_subtitle_style_tone`), reinsert `\N` (`insert_newline_tags_contextaware`), save output

## Developer Workflows

- **Run GUI:** `python main.py` (no args) or `python main_gui.py`
- **Run CLI:** `python main.py <input_file>`
- **Activate env:** `subtitle-env\Scripts\activate` (PowerShell)
- **Install deps:** `pip install -r requirements.txt` (then install torch as instructed)
- **Test core:** `python test_core_functions.py` (if present)
- **Integration demo:** `python demo_integration.py` (if present)

## Key Files & Patterns

- Tag handling: always remove `\N` before translation, reinsert after; use placeholder-based tag extraction/restoration for all tags
- Dialogue grouping: use `group_dialogue_lines`/`split_grouped_translations` for context-aware translation
- Correction: use `correct_grammar_with_fallback` (confidence threshold ≥0.6); apply glossary with `apply_glossary(text, use_context=True)`
- Style/tone: use `adjust_subtitle_style_tone` for subtitle-optimized output
- Model integration: all models loaded via `models.py:get_nllb_globals`
- Logging/progress: via `logs.py` and `progress_controller.py`
- Config: in `config.py`; thresholds in `pipeline.py`

## External Dependencies

- HuggingFace Transformers (translation/grammar)
- PyTorch (neural models, install torch separately for CUDA/CPU)
- LanguageTool Python (grammar)
- pysubs2 (subtitle parsing)
- Tkinter (GUI)

## Example Usage

- Translate: `python main.py example.srt`
- GUI: `python main.py`
- Tag/\N handling:
  - Input: `Hello,\Nworld! {\pos(320,240)}`
  - After extraction: `Hello, world!`
  - After translation: `Cześć, świecie!`
  - After reinsertion: `Cześć,\Nświecie! {\pos(320,240)}`

## Troubleshooting

- Model/language code errors: see `subtitle_workflow.py`, `models.py`
- Tag placement: see `text_tools.py`
- Dialogue grouping: see `group_dialogue_lines` in `text_tools.py`
- Correction quality: see fallback logic in `pipeline.py`
- Performance: adjust thresholds/timeouts in `pipeline.py`
- See `README.md` and code comments for more

## Key Patterns & Conventions

- **Tag Handling:**
  - Always remove `\N` before translation, reinsert contextually after
  - Use placeholders for tags, restore with `restore_tags_from_placeholders`
- **Dialogue Grouping:**
  - Use `group_dialogue_lines` (max 3 lines, idiom/context aware)
  - Split back to original lines with `split_grouped_translations`
- **Correction/Glossary:**
  - Use `correct_grammar_with_fallback` (confidence threshold: 0.6, fallback to original)
  - Apply glossary with `apply_glossary(text, use_context=True)`
- **Style/Tone:**
  - Use `adjust_subtitle_style_tone` for conversational, subtitle-optimized output
- **Model Integration:**
  - All models managed in `models.py`, language code mapping in `subtitle_workflow.py:get_model_lang_code`
- **Logging:**
  - Use `logs.py` for debug/progress tracking
- **Config:**
  - Centralized in `config.py`, thresholds in `pipeline.py`

## Developer Workflows

- **Run GUI:** `python main_gui.py` or `run_main.bat`
- **Run CLI:** `python main.py <input_file>`
- **Activate env:** `subtitle-env\Scripts\activate` (PowerShell)
- **Install deps:** `pip install -r requirements.txt`
- **Test core:** `python test_core_functions.py`
- **Integration demo:** `python demo_integration.py`

## External Dependencies

- HuggingFace Transformers (translation/grammar)
- Tkinter (GUI)
- pysubs2 (subtitle parsing)
- LanguageTool Python (grammar)
- PyTorch (neural models)
- CUDA (optional, see `CUDA-TEST.py`)

## Examples

- **Translate subtitle:** `python main.py example.srt`
- **Launch GUI:** `python main_gui.py`
- **Enhanced tag/\N:**
  - Input: `Hello,\Nworld! {\pos(320,240)}`
  - After extraction: `Hello, world!`
  - After translation: `Cześć, świecie!`
  - After reinsertion: `Cześć,\Nświecie! {\pos(320,240)}`

## Troubleshooting

- Model/language code errors: check `subtitle_workflow.py` (model mapping)
- Tag placement: use enhanced tag handling in `text_tools.py`
- Dialogue grouping: see `group_dialogue_lines` in `text_tools.py`
- Correction quality: check confidence/fallback logic in pipeline
- Performance: adjust thresholds/timeouts in `pipeline.py`
- See `README.md` and code comments for more
