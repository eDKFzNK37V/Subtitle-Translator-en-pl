# Double Model Loading Fix

## Problem

The GUI was loading the model twice when showing the review window:
1. First load: During translation (with quantization settings)
2. Second load: When showing review window (FP16 only, no quantization)

This caused:
- GUI lag/freeze while second model loaded
- Unnecessary memory usage
- Poor user experience

## Root Cause

In the `show_review` function (line 927), the code was creating a new SubtitleTranslator instance just to call `group_dialogues_by_speaker`:

```python
# OLD CODE (PROBLEMATIC)
grouped = SubtitleTranslator().group_dialogues_by_speaker(dialogues)
```

This line instantiated a whole new translator, which triggered:
- Model loading from disk
- Weight loading
- CUDA initialization
- All the overhead of creating a SubtitleTranslator

## Solution

Made `group_dialogues_by_speaker` a static method since it doesn't need the model:

```python
# NEW CODE
@staticmethod
def group_dialogues_by_speaker(dialogue_lines, enable_grouping=False):
    # ... method implementation ...
```

And updated the call:

```python
# Call as static method - no instance needed
grouped = SubtitleTranslator.group_dialogues_by_speaker(dialogues, enable_grouping=True)
```

## Benefits

1. **No double loading** - Model loads once during translation, never again
2. **Instant review window** - Appears immediately after translation
3. **No GUI lag** - No freeze or delay when showing review
4. **Better memory usage** - Only one model in memory
5. **Faster workflow** - Smoother user experience

## Additional Enhancement: Log File Updates

Also added log file updating in the review window's "Approve and Save" action:

```python
def save_and_close():
    # ... save output file ...
    
    # Update the log file with corrected translations
    log_path = output_path.rsplit('.', 1)[0] + '_log.txt'
    if os.path.exists(log_path):
        # Read existing log
        with open(log_path, 'r', encoding='utf-8') as f:
            log_lines = f.readlines()
        
        # Update translations in the log
        trans_idx = 0
        for i, line in enumerate(log_lines):
            if line.startswith('Translation:') and trans_idx < len(edited):
                log_lines[i] = f"Translation: {edited[trans_idx]}\n"
                trans_idx += 1
        
        # Write back the updated log
        with open(log_path, 'w', encoding='utf-8') as f:
            f.writelines(log_lines)
```

### Benefits of Log Updates

1. **Easier manual correction** - Corrected translations in log file
2. **Better workflow** - Log reflects final approved translations
3. **Helpful for review** - Human editors can see what was changed
4. **Consistency** - Output file and log file stay in sync

## Output Comparison

### Before Fix

```
Loading model: facebook/nllb-200-3.3B
Using device: cuda
Using 4-bit quantization
Loading checkpoint shards: 100%|███| 3/3 [00:18<00:00, 6.12s/it]
Model loaded! (FP16: True, Quantized: True)
[Translation happens]
Translation log saved to: file_pl_log.txt
Loading model: facebook/nllb-200-3.3B  ← UNWANTED SECOND LOAD
Using device: cuda
Loading checkpoint shards: 100%|███| 3/3 [00:00<00:00, 4.24it/s]
Model loaded! (FP16: True, Quantized: False)
[Review window finally shows - with lag]
```

### After Fix

```
Loading model: facebook/nllb-200-3.3B
Using device: cuda
Using 4-bit quantization
Loading checkpoint shards: 100%|███| 3/3 [00:18<00:00, 6.12s/it]
Model loaded! (FP16: True, Quantized: True)
[Translation happens]
Translation log saved to: file_pl_log.txt
[Review window shows instantly - no lag]
```

## Technical Details

### Why `group_dialogues_by_speaker` Doesn't Need the Model

The method only:
- Parses dialogue lines (text parsing)
- Extracts speaker names (string operations)
- Groups consecutive lines by speaker (list operations)

It doesn't:
- Load any models
- Use tokenizer
- Perform translation
- Access model weights

Therefore, it's a perfect candidate for a static method.

### Static Method Benefits

1. **No instance required** - Can call without creating SubtitleTranslator
2. **Clear intent** - Shows method doesn't depend on instance state
3. **Better performance** - No unnecessary object creation
4. **Cleaner API** - Method is utility function, not instance method

## Testing

- ✅ All unit tests pass
- ✅ Syntax validation passed
- ✅ No breaking changes
- ✅ Review window appears instantly
- ✅ Log file updates correctly
- ✅ Model loads only once

## Commit

Fixed in commit: `767a943` - "Fix double model loading and add log file correction on review save"
