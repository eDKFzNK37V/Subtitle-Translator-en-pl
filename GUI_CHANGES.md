# GUI Changes for Optimization Features

## New GUI Layout

The GUI has been enhanced with a new "Performance Optimizations" section.

### Before (280px height)
```
┌─────────────────────────────────────────────┐
│  File Selection                             │
│  - File path entry + Browse                 │
│  - LoRA Adapter entry + Browse              │
├─────────────────────────────────────────────┤
│  Translation Settings                       │
│  - Source/Target Language                   │
│  - File Format                              │
├─────────────────────────────────────────────┤
│  Advanced Options                           │
│  - \N index, Batch, Beams                   │
├─────────────────────────────────────────────┤
│  Progress: 0%                               │
│  Ready                                      │
│  [Start Translation]                        │
└─────────────────────────────────────────────┘
```

### After (340px height)
```
┌─────────────────────────────────────────────┐
│  File Selection                             │
│  - File path entry + Browse                 │
│  - LoRA Adapter entry + Browse              │
├─────────────────────────────────────────────┤
│  Translation Settings                       │
│  - Source/Target Language                   │
│  - File Format                              │
├─────────────────────────────────────────────┤
│  Advanced Options                           │
│  - \N index, Batch (now 32), Beams          │
├─────────────────────────────────────────────┤
│  Performance Optimizations            ← NEW │
│  ☑ FP16 (half precision)              ← NEW │
│  ☐ Quantization  Bits: [4▾]          ← NEW │
├─────────────────────────────────────────────┤
│  Progress: 0%                               │
│  Ready                                      │
│  [Start Translation]                        │
└─────────────────────────────────────────────┘
```

## New Controls

### Performance Optimizations Section
Located at row 3, after Advanced Options

**FP16 Checkbox:**
- Label: "FP16 (half precision)"
- Default: Checked (True)
- Disabled on CPU (only works on GPU)
- Provides ~1.5× speedup

**Quantization Checkbox:**
- Label: "Quantization"
- Default: Unchecked (False)
- Disabled on CPU (only works on GPU)
- Provides 2-3× speedup when enabled

**Quantization Bits Dropdown:**
- Label: "Bits:"
- Options: 4, 8
- Default: 4
- Only used when Quantization is checked
- 4-bit: Faster, less memory
- 8-bit: Better quality, more memory

## Default Values Changed

| Control    | Old Default | New Default | Reason                    |
|------------|-------------|-------------|---------------------------|
| Batch size | 8           | 32          | 3-4× faster processing    |
| FP16 mode  | N/A         | True (GPU)  | Free 1.5× speedup         |
| Window height | 280px    | 340px       | Space for new controls    |

## User Experience

### First-time Users
1. Open GUI (will see new "Performance Optimizations" section)
2. FP16 is already enabled by default (if GPU available)
3. Can optionally enable Quantization for maximum speed
4. Batch size is now 32 for faster translation

### Existing Users
1. GUI looks similar with one new section
2. Optimizations are enabled by default (non-breaking)
3. Can disable FP16 if needed for debugging
4. Backward compatible - all existing features work

## Status Messages

The model loading will now show optimization status:
```
Loading model: facebook/nllb-200-3.3B
Using device: cuda
Using 4-bit quantization
Using FP16 (half precision)
TF32 optimization enabled
Model loaded! (FP16: True, Quantized: False)
```

## Translation Log Updates

Translation logs now include optimization info:
```
Translation Setup:
  Model: facebook/nllb-200-3.3B
  Batch size: 32
  Num beams: 2
  Device: cuda
  FP16 mode: True
  Quantization: 4-bit
  LoRA adapter: None

Duration: 18.5 seconds
```

## Error Handling

### Out of Memory
If GPU runs out of memory, the system will:
1. Automatically reduce batch size (32 → 16 → 8 → 4 → 1)
2. Show warning: "⚠️ Reduced batch size to X due to OOM."
3. Continue translation with smaller batches

### No bitsandbytes
If quantization is selected but bitsandbytes is not installed:
1. Show warning message
2. Disable quantization automatically
3. Continue with FP16 or FP32

### CPU Mode
If running on CPU:
- FP16 option is automatically disabled
- Quantization option is automatically disabled
- User is notified: "Using device: cpu"
