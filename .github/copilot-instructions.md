# Subtitle-Translator-en-pl: AI Agent Coding Guide

## Project Overview & Architecture

- **Purpose:** Translate and correct English/Polish subtitles in `.ass`, `.srt`, `.txt` formats, with advanced tag handling, context-aware grouping, neural/rule-based correction, and user-driven workflows.
- **Entry Points:**
  - CLI: `main.py`
  - GUI: `main_gui.py` (calls `gui.py`, `gui_nllb.py`)
- **Core Pipeline:** `subtitle_workflow.py` (translation, correction, tag handling)
- **Batch/Context Processing:** `pipeline.py` (invokes `subtitle_workflow.py` for batch jobs)
- **Utilities:** `text_tools.py` (tag utils, dialogue grouping), `logs.py`, `resources.py`, `config.py`

### Data Flow

1. **Load subtitle** (`subtitle_workflow.py`)
2. **Preprocess:**
   - Extract `\N` tags (`text_tools.py: extract_newline_tags`)
   - Extract tag placeholders (`extract_tags_with_placeholders`)
3. **Dialogue grouping:**
   - Group lines contextually (`group_dialogue_lines`)
4. **Translate:**
   - Use selected model with glossary (`models.py`, `resources.py`)
5. **Post-process:**
   - Restore tags (`restore_tags_from_placeholders`)
   - Neural grammar correction with fallback (`correct_grammar_with_fallback`)
   - Style/tone adjustment (`adjust_subtitle_style_tone`)
   - Context-aware `\N` reinsertion (`insert_newline_tags_contextaware`)
   - Save output

## Key Patterns & Conventions

- **Tag Handling:**
  - Always remove `\N` before translation, reinsert after
  - Use placeholders for tags, restore with `restore_tags_from_placeholders`
- **Dialogue Grouping:**
  - Use `group_dialogue_lines` (max 3 lines, idiom/context aware)
  - Split back to original with `split_grouped_translations`
- **Correction/Glossary:**
  - Use `correct_grammar_with_fallback` (confidence ≥ 0.6, fallback to original)
  - Apply glossary: `apply_glossary(text, use_context=True)`
- **Style/Tone:**
  - Use `adjust_subtitle_style_tone` for subtitle-optimized output
- **Model Integration:**
  - All models in `models.py`, language code mapping in `subtitle_workflow.py:get_model_lang_code`
- **Logging:**
  - Use `logs.py` for debug/progress
- **Config:**
  - Centralized in `config.py`, thresholds in `pipeline.py`

## Developer Workflows

- **Run GUI:** `python main_gui.py` or `run_main.bat`
- **Run CLI:** `python main.py <input_file>`
- **Activate env:** `subtitle-env\Scripts\activate` (PowerShell)
- **Install deps:** `pip install -r requirements.txt`

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

## Troubleshooting & Tips

- Model/language code errors: see `subtitle_workflow.py` (model mapping)
- Tag placement: use enhanced tag handling in `text_tools.py`
- Dialogue grouping: see `group_dialogue_lines` in `text_tools.py`
- Correction quality: check confidence/fallback logic in pipeline
- Performance: adjust thresholds/timeouts in `pipeline.py`
- See `README.md` and code comments for more
