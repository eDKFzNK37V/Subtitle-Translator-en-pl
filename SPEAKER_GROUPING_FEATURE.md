# Speaker Grouping Feature

## Overview

Speaker grouping is now an **optional feature** that can be enabled for .ass subtitle files with rich character names.

## Problem Solved

The user identified that some anime subtitles have proper speaker names (e.g., "Gen", "Shizuku", "Kirito") while others don't or use generic placeholders (e.g., "NTP", "TEXT"). The grouping feature was previously forced on all files, causing issues for files without proper names.

## Solution

Made speaker grouping **user-controllable** with clear documentation on when to use it.

## How It Works

### Default Behavior (Grouping Disabled)
- Each dialogue line is translated independently
- Works reliably for all file types
- Translation logs show individual lines
- Safe for files with or without speaker names

### With Grouping Enabled
- Consecutive dialogue lines from the same speaker are grouped together
- Grouped lines are translated as one unit for better context
- Better translation quality when characters have extended dialogue
- Automatically falls back to line-by-line if names are missing

## Usage

### GUI
1. Open the application
2. Select your .ass file
3. In "Advanced Options", check **"Group by speaker (.ass only)"**
4. Click "Start Translation"

### CLI
```bash
# Enable grouping for anime with character names
python main.py anime_with_names.ass --src en --tgt pl --enable-grouping

# Default (grouping disabled) for files without names
python main.py generic_subs.ass --src en --tgt pl
```

## When to Enable Grouping

### ✅ Good Cases (Enable Grouping)
- Anime subtitles with character names in each dialogue line
- Files where speaker names are consistent (e.g., "Gen", "Shizuku")
- When the same character speaks multiple consecutive lines
- Want better contextual translation across related lines

Example:
```
Dialogue: 0,0:03:54.21,0:03:56.38,italics screener,Gen,0,0,0,,Clouds hang in the sky,
Dialogue: 0,0:03:56.38,0:03:59.42,italics screener,Gen,0,0,0,,no cars or conversations can be heard.
```

### ❌ Bad Cases (Keep Grouping Disabled)
- Files without speaker names
- Files with generic speaker names (e.g., "NTP", "TEXT", "Default")
- Files where speaker names are inconsistent or missing
- When you want individual line-by-line translation logs

Example:
```
Dialogue: 0,0:00:54.15,0:00:56.16,Default,NTP,0,0,0,,You'll find out soon enough.
Dialogue: 0,0:00:56.36,0:00:59.20,Default,NTP,0,0,0,,Once the scan reaches us.
```

## Technical Details

### Implementation
- Added `enable_grouping` parameter to `group_dialogues_by_speaker()` and `translate_ass_file()`
- Grouping disabled by default (`enable_grouping=False`)
- GUI checkbox added in Advanced Options section
- CLI flag `--enable-grouping` added

### Behavior
1. If grouping is disabled: Returns `None`, uses line-by-line translation
2. If grouping is enabled:
   - Groups consecutive lines by speaker name
   - If any line is missing a name: Falls back to line-by-line translation
   - Otherwise: Translates grouped lines together

### Code Flow
```python
# Grouping disabled (default)
grouped = group_dialogues_by_speaker(dialogues, enable_grouping=False)
# Returns: None
# Result: Line-by-line translation

# Grouping enabled
grouped = group_dialogues_by_speaker(dialogues, enable_grouping=True)
# Returns: List of groups if names present, None if names missing
# Result: Grouped translation if possible, line-by-line otherwise
```

## Benefits

### With Grouping Enabled
- Better translation context for extended character dialogue
- More natural translations for consecutive lines
- Maintains speaker's voice/tone across multiple lines

### With Grouping Disabled (Default)
- Reliable for all file types
- Predictable translation logs
- No risk of merged or corrupted translations
- Works universally regardless of speaker names

## Migration

Existing behavior is preserved - grouping is disabled by default. Users who want the grouping feature for specific files can explicitly enable it.

No breaking changes - all existing workflows continue to work as before.

## Documentation

- Updated OPTIMIZATION_GUIDE.md with detailed speaker grouping section
- Updated README.md with `--enable-grouping` option
- In-code documentation explains when to use the feature

## Testing

- All unit tests pass
- Syntax validation passed
- Feature is opt-in, so existing functionality unchanged
- Safe fallback behavior if names are missing
