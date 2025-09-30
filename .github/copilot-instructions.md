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