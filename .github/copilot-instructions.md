# Copilot Instructions for Subtitle-Translator-en-pl

## Project Overview

- **Purpose:** Translate and correct subtitle files between English and Polish, supporting `.ass`, `.srt`, and `.txt` formats. Focus on robust tag handling, context-aware dialogue grouping, neural and rule-based correction, and user-driven translation workflows.
- **Entry Points:**
  - `main.py` (CLI), `main_gui.py` (GUI)
  - GUI logic: `gui.py`, `gui_m2m100.py`, `gui_nllb.py`
  - Core pipeline: `subtitle_workflow.py` (translation/correction logic, tag handling)
  - Utilities: `text_tools.py` (tag utils, dialogue grouping), `grammar.py`, `logs.py`, `resources.py`, `config.py`

## Architecture & Data Flow

- **Enhanced Pipeline:**
  1. Load subtitle file (`subtitle_workflow.py`)
  2. Preprocess: extract all `\N` tags (see `text_tools.py: extract_newline_tags`), extract tag placeholders with semantic positioning (see `extract_tags_with_placeholders`)
  3. Enhanced dialogue grouping: group consecutive lines using idiom detection and context preservation (see `text_tools.py: group_dialogue_lines`)
  4. Translate using selected model with enhanced glossary (`subtitle_workflow.py`, `models.py`)
  5. Post-process:
     - Restore tags with intelligent spacing and word boundary detection (see `text_tools.py: restore_tags_from_placeholders`)
     - Neural grammar correction with confidence scoring and fallback (T5-based, see `text_tools.py: correct_grammar_with_fallback`)
     - LanguageTool correction with timeout protection (`grammar.py`)
     - Style/tone adjustment for subtitle context (see `text_tools.py: adjust_subtitle_style_tone`)
     - Enhanced glossary/consistency check with context-awareness (see `resources.py: ENHANCED_GLOSSARY`)
     - Context-aware `\N` reinsertion using punctuation/clause boundaries (see `insert_newline_tags_contextaware`)
     - Confidence-based fallback throughout to avoid over-correction
     - Save output
- **GUI:**
  - Built with `tkinter` (`gui.py`, `gui_m2m100.py`, `gui_nllb.py`)
  - Model selection, progress tracking, and user-configurable `\N` reinsertion index (Spinbox)
  - Enhanced progress display with ETA and separate translation/post-processing phases
- **Batch/Context-Aware Processing:**
  - `pipeline.py` provides enhanced batch correction and context-aware translation, always calling into `subtitle_workflow.py`

## Developer Workflows

- **Run GUI:**
  - `python main_gui.py` or `run_main.bat` (Windows)
- **Run CLI:**
  - `python main.py <input_file>`
- **Environment:**
  - Use the `subtitle-env` virtual environment: `subtitle-env\Scripts\activate` (PowerShell)
  - Dependencies: `requirements.txt`
- **Testing:**
  - Core function tests: `python test_core_functions.py`
  - Integration demo: `python demo_integration.py`
  - Validate by running translation on sample files

## Project-Specific Patterns

- **Enhanced Tag Handling & Placeholders:**
  - All `\N` tags are removed before translation and reinserted using context-aware logic
  - Tag placeholders with semantic positioning using relative word positions and intelligent spacing
  - Use `extract_tags_with_placeholders` and `restore_tags_from_placeholders` in `text_tools.py`
  - Always preserve original tag formatting and prevent tag-word collisions

- **Context-Aware `\N` Reinsertion:**
  - Use `insert_newline_tags_contextaware` for punctuation/clause boundary placement
  - Fallback to `insert_newline_tags_at_wordidx` for word-index based placement
  - Priority: punctuation breaks > conjunctions > natural pauses > word boundaries

- **Enhanced Dialogue Grouping:**
  - Use improved `group_dialogue_lines` with idiom detection and context preservation
  - Detects common phrases that shouldn't be split
  - Maximum group size of 3 lines to prevent over-grouping
  - Smart splitting back to original lines with `split_grouped_translations`

- **Confidence-Based Correction:**
  - Use `correct_grammar_with_fallback` and `correct_grammar_batch` with confidence thresholds
  - Default confidence threshold: 0.6 (configurable via `CONFIDENCE_THRESHOLD` in `pipeline.py`)
  - Fallback to original text when confidence is below threshold

- **Enhanced Glossary System:**
  - Use `ENHANCED_GLOSSARY` (50+ terms) in `resources.py` with context-sensitive translations
  - Apply via `apply_glossary(text, use_context=True)` for context-aware term replacement
  - Context detection based on domain keywords (gaming, business, technology)

- **Style/Tone Adjustment:**
  - Use `adjust_subtitle_style_tone` for language-specific subtitle optimizations
  - Conversational tone (contractions, simplified phrases)
  - Punctuation normalization and spacing fixes
  - Language-specific patterns for Polish and English

- **Model Integration:**
  - Model-specific GUIs: `gui_m2m100.py`, `gui_nllb.py`
  - All models managed in `models.py`
  - Language code mapping is model-specific (see `get_model_lang_code` in `subtitle_workflow.py`)

- **Cross-Component Patterns:**
  - Both GUI and CLI use the same enhanced translation pipeline in `subtitle_workflow.py`
  - Logging via `logs.py` with debug-level progress tracking
  - Avoid circular imports by importing GUI entry points only inside functions

- **Configuration:**
  - Centralized in `config.py`
  - Confidence thresholds, timeouts, and processing parameters in `pipeline.py`

- **Resource Management:**
  - Enhanced static resources and expanded glossary in `resources.py`
  - Context-sensitive term detection and application

## External Dependencies

- **HuggingFace Transformers** for translation and grammar models
- **Tkinter** for GUI
- **pysubs2** for subtitle parsing
- **LanguageTool Python** for grammar checking
- **PyTorch** for neural models
- **CUDA** support is optional (`CUDA-TEST.py`)

## Conventions & Examples

- **File Naming:** GUI files prefixed with `gui_`, model logic in `models.py`, enhanced pipeline in `pipeline.py`
- **Error Handling:** Most errors are logged with graceful fallbacks to prevent pipeline failures
- **Testing:** Use `test_core_functions.py` for validation, `demo_integration.py` for workflow examples
- **To translate a subtitle:** `python main.py example.srt`
- **To launch the GUI:** `python main_gui.py`
- **Enhanced Tag/\N Example:**
  - Input: `Hello,\Nworld! {\pos(320,240)}`
  - After extraction: `Hello, world!` (with tag count and placeholder map)
  - After translation/correction: `Cześć, świecie!`
  - After context-aware reinsertion: `Cześć,\Nświecie! {\pos(320,240)}`

## Recent Enhancements

- **Improved Tag Restoration:** Semantic positioning with intelligent spacing
- **Context-Aware \N Insertion:** Punctuation and clause boundary detection
- **Confidence-Based Fallback:** Smart correction with quality assessment
- **Enhanced Dialogue Grouping:** Idiom preservation and context awareness
- **Expanded Glossary:** 50+ terms with context-sensitive translations
- **Style/Tone Adjustment:** Subtitle-specific optimizations for natural speech
- **Comprehensive Testing:** Core function validation and integration demos

## Troubleshooting

- For model/language code errors, see `subtitle_workflow.py` and ensure correct mapping for the selected model
- For tag placement issues, check that enhanced tag handling is used via `text_tools.py` utilities
- For dialogue grouping/fragmentation, review improved `group_dialogue_lines` with idiom detection
- For correction quality, check confidence scores and fallback logic in enhanced pipeline
- For performance issues, adjust confidence thresholds and timeout values in `pipeline.py`
- Refer to `README.md`, test files, and code comments for further usage and architecture details
