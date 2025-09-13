# Copilot Instructions for Subtitle-Translator-en-pl

## Project Overview

- **Purpose:** Translate and correct subtitle files between English and Polish, supporting `.ass`, `.srt`, and `.txt` formats.
- **Entry Points:**
  - `main.py` (CLI), `main_gui.py` (GUI)
  - GUI logic: `gui.py`, `gui_m2m100.py`, `gui_nllb.py`
  - Core pipeline: `subtitle_workflow.py` (all translation/correction logic)
  - Utilities: `grammar.py`, `text_tools.py`, `logs.py`, `resources.py`, `config.py`

## Architecture & Data Flow

- **Pipeline:**
  1. Load subtitle file (see `subtitle_workflow.py`)
  2. Preprocess and (optionally) grammar-check (`grammar.py`)
  3. Translate using selected model (`subtitle_workflow.py`, `models.py`)
  4. Post-process and save output
- **GUI:**
  - Built with `tkinter` (`gui.py` and model-specific GUIs)
  - Model selection and progress: `gui_m2m100.py`, `gui_nllb.py`, `progress_controller.py`
- **Batch/Context-Aware Processing:**
  - `pipeline.py` provides batch correction and context-aware translation, always calling into `subtitle_workflow.py` for model logic

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

- **Model Integration:**
  - Model-specific GUIs: `gui_m2m100.py`, `gui_nllb.py`
  - All models managed in `models.py`
  - Language code mapping is model-specific: NLLB uses codes like `eng_Latn`, M2M100 uses `en`. See `get_model_lang_code` in `subtitle_workflow.py` for mapping logic
  - When adding new models, update `models.py`, `subtitle_workflow.py` (language code mapping), and add a new `gui_<model>.py` if GUI support is needed
- **Cross-Component Patterns:**
  - Both GUI and CLI use the same translation pipeline in `subtitle_workflow.py`
  - Logging is handled via `logs.py` (not shown to user by default)
  - Circular import issues are avoided by importing GUI entry points only inside functions
  - If you see KeyError for language codes, check the mapping for the selected model
- **Configuration:**
  - Centralized in `config.py`
- **Resource Management:**
  - Static resources and language files in `resources.py`

## External Dependencies

- **HuggingFace Transformers** for translation models
- **Tkinter** for GUI
- **pysubs2** for subtitle parsing
- **CUDA** support is optional (`CUDA-TEST.py`)

## Conventions & Examples

- **File Naming:** GUI files prefixed with `gui_`, model logic in `models.py`, pipeline in `pipeline.py`
- **Error Handling:** Most errors are logged, not raised to the user
- **To translate a subtitle:** `python main.py example.srt`
- **To launch the GUI:** `python main_gui.py`

## Troubleshooting

- For model/language code errors, see `subtitle_workflow.py` and ensure correct mapping for the selected model
- Refer to `README.md` and code comments for further usage and architecture details
