# COMPLETE FUNCTION LIST FOR TROUBLESHOOTING
## Subtitle-Translator-en-pl Repository Analysis

This document provides a comprehensive list of ALL functions in the main directory, organized by file, with their usage information for troubleshooting purposes.

Generated using the `function_analyzer.py` script following the copilot-instructions.md patterns.

---

## SUMMARY STATISTICS
- **Total function definitions:** 153
- **Unique function names:** 140  
- **Total function calls:** 1,648
- **Functions called but not defined locally:** 264 (external/imported)

---

## FUNCTIONS BY FILE WITH USAGE INFORMATION

### config.py
*No user-defined functions (only constants and imports)*

### function_analyzer.py
**Class FunctionAnalyzer:**
- `__init__(self, root_dir)` [Line 41] - ⚠️ NOT CALLED (automatic constructor)
- `analyze_directory(self)` [Line 47] - Called in: function_analyzer.py:311
- `_analyze_file(self, file_path)` [Line 61] - Called in: function_analyzer.py:56  
- `_extract_functions(self, tree, file_path)` [Line 81] - Called in: function_analyzer.py:73
- `_extract_function_calls(self, tree, file_path, lines)` [Line 124] - Called in: function_analyzer.py:76
- `_get_function_name_from_call(self, call_node)` [Line 146] - Called in: function_analyzer.py:128
- `_extract_imports(self, tree, file_path)` [Line 160] - Called in: function_analyzer.py:79
- `find_unused_functions(self)` [Line 176] - Called in: function_analyzer.py:259
- `generate_report(self)` [Line 193] - Called in: function_analyzer.py:297
- `save_report(self, output_file)` [Line 295] - Called in: function_analyzer.py:315

**Standalone Functions:**
- `main()` [Line 302] - Called in: main.py:241, function_analyzer.py:323

### gui.py
- `handle_exception(exc_type, exc_value, exc_traceback)` [Line 9] - ⚠️ NOT CALLED (potential unused function)
- `run_gui()` [Line 29] - Called in: subtitle_workflow.py:12, main.py:85

### gui_nllb.py
**Main GUI Functions:**
- `run_gui_nllb()` [Line 16] - Called in: gui.py:34
- `browse_file()` [Line 364] - Called in: gui_nllb.py:39, gui_nllb.py:40
- `start_translation()` [Line 573] - Called in: gui_nllb.py:839

**Widget/UI Helper Functions:**  
- `update_formatting_widgets()` [Line 77] - Called in: gui_nllb.py:104
- `show_txt_preserve_formatting_popup(txt_path)` [Line 372] - Called in: gui_nllb.py:72
- `apply_preset(preset_name)` [Line 200] - Called in: gui_nllb.py:231, gui_nllb.py:233, gui_nllb.py:235

**Translation/Review Functions:**
- `on_translation_success(out_path, log_path, start_time)` [Line 861] - Called in: gui_nllb.py:470, gui_nllb.py:562
- `on_translation_error(err)` [Line 881] - Called in: 6 places across gui_nllb.py
- `show_flexion_preview(lines)` [Line 394] - Called in: gui_nllb.py:478, gui_nllb.py:570

**⚠️ UNUSED Functions in gui_nllb.py:**
- `validate_beams(value)` [Line 112] - NOT CALLED
- `validate_penalty_temp(value)` [Line 119] - NOT CALLED  
- `validate_batch_size(value)` [Line 126] - NOT CALLED
- `reset_parameters()` [Line 239] - NOT CALLED
- `show_help()` [Line 253] - NOT CALLED
- `review_txt_translations()` [Line 392] - NOT CALLED
- `review_sub_translations()` [Line 480] - NOT CALLED
- `run_and_reset()` [Line 837] - NOT CALLED
- `start_translation_thread()` [Line 843] - NOT CALLED

### logs.py
**Class CLIEventData:**
- `__init__(self, ...)` [Line 12] - ⚠️ NOT CALLED (automatic constructor)
- `to_dict(self)` [Line 27] - Called in: logs.py:79

**Class CLICallbackManager:**
- `__init__(self)` [Line 49] - ⚠️ NOT CALLED (automatic constructor)
- `register_callback(self, event_type, callback)` [Line 69] - Called in: logs.py:591
- `_dispatch_event(self, event_data)` [Line 76] - Called in: 4 places in logs.py
- `on_start(self, ...)` [Line 101] - Called in: logs.py:571
- `on_progress(self, ...)` [Line 132] - Called in: logs.py:576
- `on_finish(self, ...)` [Line 150] - Called in: logs.py:581
- `on_error(self, ...)` [Line 167] - Called in: logs.py:586
- `get_session_summary(self)` [Line 186] - ⚠️ NOT CALLED

**Class SubtitleLogger:**
- `__init__(self, file_path, target_lang, idx_map)` [Line 205] - ⚠️ NOT CALLED (automatic constructor)
- `_make_log_path(self, file_path)` [Line 213] - Called in: logs.py:211
- `log_entry(self, ...)` [Line 227] - Called in: gui_nllb.py:808, main.py:207
- `write_summary(self)` [Line 242] - Called in: gui_nllb.py:812, main.py:213
- `get_log_path(self)` [Line 284] - Called in: gui_nllb.py:816, main.py:214

**Standalone Functions:**
- `get_next_correction_log_path(output_dir)` [Line 297] - Called in: logs.py:318
- `initialize_session_log(output_dir)` [Line 313] - Called in: 4 places across files
- `is_likely_unknown_word(word)` [Line 328] - Called in: logs.py:451, logs.py:466
- `accumulate_correction_data(original_lines, corrected_lines)` [Line 431] - Called in: logs.py:561, pipeline.py:182
- `write_session_log()` [Line 477] - Called in: subtitle_workflow.py:457, logs.py:182
- `log_names_and_unknown_words(original_lines, corrected_lines, log_file)` [Line 557] - Called in: text_tools.py:662

**CLI Convenience Functions:**
- `on_cli_start(...)` [Line 569] - Called in: main.py:115
- `on_cli_progress(...)` [Line 574] - ⚠️ NOT CALLED
- `on_cli_finish(...)` [Line 579] - Called in: main.py:224
- `on_cli_error(...)` [Line 584] - Called in: 6 places in main.py
- `register_cli_callback(...)` [Line 589] - ⚠️ NOT CALLED

### main.py
- `print_usage()` [Line 8] - Called in: main.py:77, main.py:81
- `create_translation_callback(stage_name)` [Line 42] - Called in: main.py:157
- `create_post_processing_callback()` [Line 51] - Called in: main.py:181
- `main()` [Line 60] - Called in: main.py:241, function_analyzer.py:323

**Nested Functions in main.py:**
- `callback(current, total)` [Line 44] - Called in: logs.py:97
- `callback(current, total)` [Line 53] - Called in: logs.py:97

### models.py
- `get_nllb_globals()` [Line 46] - Called in: subtitle_workflow.py:29, gui_nllb.py:11, main.py:119

### pipeline.py
**Core Processing Functions:**
- `apply_glossary(text, glossary, use_context)` [Line 50] - Called in: 7 places across files
- `correct_text(text, lang)` [Line 71] - ⚠️ NOT CALLED
- `correct_text_batch(lines, lang, progress_callback)` [Line 112] - ⚠️ NOT CALLED
- `translate_with_context(...)` [Line 198] - ⚠️ NOT CALLED

**Helper Functions:**
- `_clamp(text, max_chars)` [Line 28] - Called in: 3 places in pipeline.py
- `_lt_check_with_timeout(tool, text, timeout_sec)` [Line 31] - Called in: 2 places in pipeline.py
- `run()` [Line 33] - ⚠️ NOT CALLED

### polish_morphology.py
- `enhance_polish_conjugation(text)` [Line 81] - Called in: 2 places in pipeline.py, text_tools.py:181
- `_fix_verb_conjugation(text)` [Line 112] - Called in: polish_morphology.py:105
- `_fix_adjective_agreement(text)` [Line 125] - Called in: polish_morphology.py:108
- `improve_polish_style(text)` [Line 136] - Called in: 2 places in pipeline.py, subtitle_workflow.py:567
- `_improve_word_order(text)` [Line 168] - Called in: polish_morphology.py:164
- `validate_polish_text(text)` [Line 181] - ⚠️ NOT CALLED

### progress_controller.py
**Class ProgressController:**
- `__init__(self, ...)` [Line 5] - ⚠️ NOT CALLED (automatic constructor)
- `start(self, translation_lines)` [Line 23] - Called in: gui_nllb.py:630
- `set_post_total(self, post_total)` [Line 39] - Called in: gui_nllb.py:672
- `_step_ui(self, steps)` [Line 68] - Called in: progress_controller.py:112, progress_controller.py:151
- `update_translation_progress(self, current, total)` [Line 88] - ⚠️ NOT CALLED DIRECTLY (used as callback)
- `_do_translation_update(self, current, total)` [Line 100] - Called in: progress_controller.py:93
- `update_post_progress(self, current, total)` [Line 121] - Called in: 15 places in gui_nllb.py
- `_do_post_update(self, current, total)` [Line 133] - Called in: progress_controller.py:126
- `show_post_start(self)` [Line 169] - ⚠️ NOT CALLED DIRECTLY (used as callback)
- `reset_ui(self)` [Line 180] - Called in: progress_controller.py:187
- `reset(self)` [Line 186] - Called in: gui_nllb.py:826, gui_nllb.py:876, gui_nllb.py:892
- `_update_ui(self, pct, status)` [Line 199] - Called in: 5 places in progress_controller.py

### resources.py
- `get_context_from_text(text)` [Line 175] - Called in: resources.py:208
- `apply_context_sensitive_glossary(text, context)` [Line 203] - Called in: pipeline.py:63

### subtitle_workflow.py
**Main Translation Functions:**
- `translate_with_context_nllb(...)` [Line 165] - Called in: gui_nllb.py:642, main.py:148
- `correct_text_batch_nllb(...)` [Line 251] - Called in: 3 places across files
- `translate_lines(...)` [Line 339] - Called in: subtitle_workflow.py:362, subtitle_workflow.py:425
- `translate_batch(...)` [Line 461] - Called in: subtitle_workflow.py:362, subtitle_workflow.py:425

**Model/Setup Functions:**
- `model_setup()` [Line 26] - Called in: 7 places across files
- `get_model_lang_code(lang, model_type)` [Line 38] - Called in: 6 places in subtitle_workflow.py
- `translate_batch_nllb(...)` [Line 52] - Called in: subtitle_workflow.py:149, subtitle_workflow.py:229
- `translate_lines_nllb(...)` [Line 135] - Called in: subtitle_workflow.py:149, subtitle_workflow.py:229

**Helper Functions:**
- `_get_target_lang_from_code(lang_code)` [Line 14] - Called in: subtitle_workflow.py:125
- `_enhance_translation_quality(...)` [Line 535] - Called in: subtitle_workflow.py:128, subtitle_workflow.py:527
- `_basic_polish_improvements(text)` [Line 579] - Called in: subtitle_workflow.py:570

**⚠️ UNUSED Functions in subtitle_workflow.py:**
- `run_gui_entry()` [Line 10] - NOT CALLED
- `load_nllb_13b()` [Line 42] - NOT CALLED
- `translate_subtitles(...)` [Line 377] - NOT CALLED

### text_tools.py
**Grammar/Correction Functions:**
- `correct_punctuation(text, model_choice)` [Line 8] - Called in: pipeline.py:93
- `correct_grammar(text, num_beams, confidence_threshold)` [Line 38] - Called in: text_tools.py:197
- `correct_grammar_with_fallback(text, confidence_threshold)` [Line 162] - Called in: 3 places across files
- `clean_translation(text)` [Line 237] - Called in: 5 places across files

**Tag/Text Processing Functions:**
- `group_dialogue_lines(lines)` [Line 251] - Called in: 7 places across files
- `split_grouped_translations(translated_groups, mapping)` [Line 347] - Called in: 7 places across files
- `extract_newline_tags(text)` [Line 370] - Called in: 3 places across files
- `insert_newline_tags_at_wordidx(text, n_tags, word_idx)` [Line 379] - Called in: 3 places across files
- `insert_newline_tags_contextaware(text, n_tags, prefer_punctuation)` [Line 423] - Called in: 4 places across files
- `extract_tags_with_placeholders(text)` [Line 519] - Called in: 9 places across files
- `restore_tags_from_placeholders(translated, ph_map)` [Line 539] - Called in: 11 places across files

**Style/Enhancement Functions:**
- `adjust_subtitle_style_tone(text, target_lang)` [Line 706] - Called in: 3 places across files
- `detect_and_improve_formality(text, target_lang)` [Line 756] - Called in: pipeline.py:100
- `fix_common_translation_issues(text, target_lang)` [Line 766] - Called in: 2 places in pipeline.py

**Validation/Analysis Functions:**
- `count_polish_characters(text)` [Line 103] - Called in: 4 places in text_tools.py
- `detect_proper_names(text)` [Line 111] - Called in: 2 places in text_tools.py
- `validate_character_preservation(...)` [Line 123] - Called in: 2 places in text_tools.py
- `validate_name_preservation(original, corrected)` [Line 144] - Called in: text_tools.py:214

**Helper Functions:**
- `should_continue_group(prev_line, curr_line)` [Line 267] - Called in: text_tools.py:316
- `is_natural_break(line)` [Line 292] - Called in: text_tools.py:335
- `clean_duplicate_newline_tags(text)` [Line 412] - Called in: gui_nllb.py:803
- `normalize_tag(tag)` [Line 561] - Called in: 2 places in text_tools.py
- `find_optimal_insertion_point(...)` [Line 576] - Called in: text_tools.py:638
- `insert_tag_with_smart_spacing(...)` [Line 610] - Called in: text_tools.py:639

**⚠️ UNUSED Functions in text_tools.py:**
- `calculate_text_similarity_confidence(original, corrected)` [Line 78] - NOT CALLED
- `extract_tags(text)` [Line 243] - NOT CALLED
- `restore_tags(translated, tags)` [Line 496] - NOT CALLED
- `strip_subtitle_tags(text)` [Line 501] - NOT CALLED
- `correct_grammar_batch(texts, ...)` [Line 646] - NOT CALLED
- `correct_punctuation_batch(texts, model_choice)` [Line 668] - NOT CALLED
- `repl(m)` [Line 528] - NOT CALLED (nested function)

### utils.py
**File I/O Functions:**
- `detect_encoding(file_path)` [Line 11] - Called in: 3 places in utils.py
- `load_subtitle_lines(path)` [Line 18] - Called in: 5 places across files
- `save_subtitle_lines(lines, file_path, subs, idx_map)` [Line 49] - Called in: 6 places across files

**⚠️ UNUSED Functions in utils.py:**
- `clean_translation(text)` [Line 93] - DUPLICATE (also in text_tools.py)
- `extract_tags(text)` [Line 98] - NOT CALLED
- `restore_tags(text, tags)` [Line 103] - NOT CALLED

---

## CRITICAL UNUSED FUNCTIONS (POTENTIAL ISSUES)

These functions are defined but never called, which may indicate:
1. **Dead code** that can be removed
2. **Missing functionality** that should be connected
3. **Incomplete features** that need implementation

### High Priority (Core Features):
- `translate_subtitles()` in subtitle_workflow.py - Main translation function not called
- `correct_text_batch()` in pipeline.py - Core correction function not called
- `translate_with_context()` in pipeline.py - Context translation not called

### Medium Priority (GUI Features):
- `start_translation_thread()` in gui_nllb.py - Threading function not called
- `review_txt_translations()` in gui_nllb.py - Review dialog not called
- `review_sub_translations()` in gui_nllb.py - Review dialog not called
- Various validation functions in gui_nllb.py

### Low Priority (Utility/Helper):
- Multiple `extract_tags()` and `restore_tags()` functions - Legacy/duplicate code
- Polish morphology validation functions
- Session management functions

---

## RECOMMENDATIONS FOR TROUBLESHOOTING

1. **Check unused core functions** - Some critical translation functions aren't being called
2. **Review GUI workflow** - Several dialog and validation functions are disconnected  
3. **Remove duplicate code** - Multiple versions of tag extraction/restoration functions
4. **Implement missing connections** - Link unused validation and review functions
5. **Clean up legacy code** - Remove truly unused utility functions

This analysis provides a complete map of the codebase for debugging and maintenance purposes.