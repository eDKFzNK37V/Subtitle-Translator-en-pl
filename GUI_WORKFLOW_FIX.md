# GUI Workflow Fix

## Problem

The GUI review window wasn't properly handling the approve and cancel actions:
- "Approve and Save" just closed the window without saving edits
- "Cancel" just closed the window without cleaning up files
- No clear indication of what happened after each action

## Solution

Implemented proper workflow as requested by the user:

### Expected Workflow

1. **GUI starts** - Ready state
2. **User chooses settings** - Configure translation parameters
3. **Click "Start Translation"** - Model loads (first time only)
4. **Translation runs** - Progress shown
5. **Translation completes** - Model stays loaded in memory
6. **Review window appears** - No model reloading
7. **User approves OR cancels**:
   - **Approve**: Saves any edits to output file
   - **Cancel**: Deletes output files and shows cancellation message
8. **Ready for next translation** - Model still loaded, UI reset

### Implementation Details

#### "Approve and Save" Button
```python
def save_and_close():
    """Save edited translations and finalize the output file."""
    edited = [e.get() for e in entry_widgets]
    
    # Apply edits to the output file
    # - For .ass: Update dialogue lines with edited translations
    # - For .srt: Update subtitle text blocks
    # - For .txt: Rewrite entire file with edited lines
    
    # Show success message
    messagebox.showinfo("Success", f"Translation saved!\n\nOutput: {output_path}")
    reset_ui()
```

**What it does:**
1. Collects all edited translations from the entry widgets
2. Reads the output file
3. Updates the relevant parts with user edits
4. Writes back to the same file (overwrites)
5. Shows success message with output path
6. Resets UI for next translation

#### "Cancel" Button
```python
def cancel_translation():
    """Cancel the translation and delete the output file."""
    # Delete the output file
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # Delete the log file if it exists
    log_path = output_path.rsplit('.', 1)[0] + '_log.txt'
    if os.path.exists(log_path):
        os.remove(log_path)
    
    # Show cancellation message
    messagebox.showinfo("Cancelled", "Translation cancelled. Output files deleted.")
    reset_ui()
```

**What it does:**
1. Deletes the output translation file
2. Deletes the associated log file
3. Shows cancellation message
4. Resets UI for next translation

#### Visual Changes
- Cancel button now has red background (`bg="#f44336"`) to indicate destructive action
- Both buttons have white text for better contrast

### Benefits

1. **Clear actions**: User knows exactly what happened
2. **File cleanup**: No leftover files when cancelling
3. **Edit support**: User edits are properly saved
4. **Model persistence**: Model stays loaded between translations (faster subsequent runs)
5. **Better UX**: Color-coded buttons, clear messages

### File Format Handling

#### .ass Files
- Parses dialogue lines: `Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text`
- Updates the 10th field (Text) with edited translation
- Preserves all timing, style, and metadata

#### .srt Files
- Finds subtitle blocks (index, timestamp, text)
- Replaces text portion with edited translation
- Preserves timing and index numbering

#### .txt Files
- Simple line-by-line replacement
- Rewrites entire file with edited lines

### Error Handling

Both approve and cancel actions have try-except blocks:
- Catches file I/O errors
- Shows error messages to user
- Ensures UI is reset even if something fails
- Review window is always closed

### Testing

- ✅ All unit tests pass
- ✅ Syntax validation passed
- ✅ No breaking changes to existing functionality
- ✅ Model persistence verified
- ✅ File deletion on cancel verified

## Usage

### Normal Workflow
1. Open GUI
2. Select file and configure settings
3. Click "Start Translation"
4. Wait for translation (model loads first time only)
5. Review window appears
6. Make any edits if needed
7. Click "Approve and Save"
8. Success message shows file location
9. Ready for next file (model still loaded)

### Cancellation Workflow
1. Follow steps 1-6 above
2. Decide not to keep translation
3. Click "Cancel"
4. Output files are deleted
5. Cancellation message appears
6. Ready for next file (model still loaded)

## Technical Notes

### Model Persistence
The `translator` variable is stored as a `nonlocal` variable in the GUI scope:
```python
translator = None

def start_translation():
    nonlocal translator
    
    if translator is None:
        # Load model (only happens once)
        translator = SubtitleTranslator(...)
```

This ensures:
- Model is loaded once on first translation
- Subsequent translations reuse the loaded model
- Much faster for processing multiple files
- Model only unloads when GUI window is closed

### Thread Safety
Translation runs in a background thread to keep GUI responsive:
- Model loading happens in thread
- Translation happens in thread
- UI updates are marshaled to main thread via `root.after()`
- Review window appears on main thread

## Future Enhancements

Potential improvements (not in scope):
1. Undo/redo for edits in review window
2. Export edits to external file
3. Compare original vs edited side-by-side
4. Keyboard shortcuts for approve/cancel
5. Remember last used settings

## Commit

Fixed in commit: `d305902` - "Fix GUI workflow: properly handle review window approve/cancel actions"
