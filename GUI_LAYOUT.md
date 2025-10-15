# GUI Layout - Simplified Subtitle Translator

```
┌─────────────────────────────────────────────────────────────┐
│  Subtitle Translator (NLLB)                            [_][□][X] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Subtitle File:  [________________________________] [Browse] │
│                                                             │
│  Source Language:    [en ▼]                                │
│                                                             │
│  Target Language:    [pl ▼]                                │
│                                                             │
│  File Type:          [ass ▼]                               │
│                                                             │
│  \N tag word index:  [5 ▼]                    (0 = auto)   │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Translation: 45%                                           │
│                                                             │
│  Ready                                                      │
│                                                             │
│              [ Start Translation ]                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Language Options: en, pl, ja, fr, de
File Type Options: ass, srt, txt
```

## Features Shown:

1. **File Browser** - Simple entry field with browse button
2. **Language Selection** - Dropdown menus for source and target
3. **File Type** - Dropdown to select .ass, .srt, or .txt
4. **\N Tag Index** - Spinbox (0-50) for line break control in .ass files
5. **Progress Display** - Shows translation percentage
6. **Status Label** - Shows current state (Ready, Translating, Complete)
7. **Start Button** - Initiates translation

## Removed from Previous Version:

- Quality presets (Quality, Speed, Creative buttons)
- Advanced translation parameters
- Polish Only checkbox  
- Preserve formatting checkbox (auto-detected)
- Preview button
- Multiple progress bars
- Complex preset management
- Reset and Help buttons

## Clean, Minimal Design:

- Only essential controls
- Clear, straightforward layout
- Matches reference image provided by user
- No confusing options or presets
- Threading prevents UI freeze
- Review window appears after translation
