# Subtitle-Translator-en-pl: AI Agent Coding Guide

## Project Purpose & Architecture

- **Goal:** Translate and correct subtitles (English/Polish) in `.ass`, `.srt`, `.txt` formats, with robust tag handling, context-aware grouping, neural/rule-based correction, and user-driven workflows.
- **Main entry points:**
  - CLI: `main.py`
  - GUI: `main_gui.py` (calls into `gui.py`, `gui_m2m100.py`, `gui_nllb.py`)
- **Core pipeline:** `subtitle_workflow.py` (translation/correction, tag handling)
- **Utilities:** `text_tools.py` (tag utils, dialogue grouping), `grammar.py`, `logs.py`, `resources.py`, `config.py`
- **Batch/context-aware processing:** `pipeline.py` (always calls `subtitle_workflow.py`)

### Data Flow (Pipeline)

1. **Load subtitle** (`subtitle_workflow.py`)
2. **Preprocess:**
   - Extract all `\N` tags (`text_tools.py: extract_newline_tags`)
   - Extract tag placeholders with semantic positioning (`extract_tags_with_placeholders`)
3. **Dialogue grouping:**
   - Group consecutive lines using idiom/context detection (`group_dialogue_lines`)
4. **Translate:**
   - Use selected model with enhanced glossary (`models.py`, `resources.py`)
5. **Post-process:**
   - Restore tags with intelligent spacing/word boundary detection (`restore_tags_from_placeholders`)
   - Neural grammar correction with confidence scoring/fallback (`correct_grammar_with_fallback`)
   - LanguageTool correction with timeout (`grammar.py`)
   - Style/tone adjustment for subtitles (`adjust_subtitle_style_tone`)
   - Context-aware `\N` reinsertion (`insert_newline_tags_contextaware`)
   - Save output

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
