# Bug Fix: Dialogue Grouping Issue

## Problem

The speaker grouping feature was causing merged dialogue lines to appear in translation logs instead of individual lines. 

Example of incorrect output:
```
[Line 1]
Original:    Don't get too tense. Don't treat me like a newbie! And don't you need to get your weapon serviced, Kirito?
Translation: Nie bądź zbyt spięty. Nie traktuj mnie jak nowicjusza! A czy nie musisz obsługiwać swojej broni, Kirito?
```

Expected output:
```
[Line 1]
Original:    Don't get too tense.
Translation: Nie bądź zbyt spięty.

[Line 2]
Original:    Don't treat me like a newbie!
Translation: Nie traktuj mnie jak nowicjusza!

[Line 3]
Original:    And don't you need to get your weapon serviced, Kirito?
Translation: A czy nie musisz obsługiwać swojej broni, Kirito?
```

## Root Cause

The `group_dialogues_by_speaker()` function was:
1. Merging consecutive dialogue lines from the same speaker into a single text
2. Translating the merged text as one unit
3. Attempting to split the translation back into individual lines by splitting on spaces

This naive split approach was fundamentally flawed because:
- Splitting on spaces doesn't respect sentence boundaries
- It could break words or sentences in the middle
- The split points rarely aligned with the original line breaks

## Solution

Disabled the speaker grouping feature by making `group_dialogues_by_speaker()` always return `None`. 

This forces the code to use the more reliable line-by-line translation path where:
- Each dialogue line is extracted individually
- Each line is translated independently
- Each translation is written back to its original dialogue line
- Translation logs show individual lines as expected

## Code Change

```python
def group_dialogues_by_speaker(self, dialogue_lines):
    """
    Group consecutive dialogue lines by the same speaker (if names detected).
    
    NOTE: Grouping is currently disabled as it causes issues with splitting
    translated text back into individual dialogue lines. Line-by-line 
    translation is more reliable.
    """
    # Grouping disabled - always return None to use line-by-line translation
    return None
```

## Impact

- ✅ Translation logs now show individual dialogue lines
- ✅ Each line is translated independently and accurately
- ✅ No breaking of sentences or words in the middle
- ✅ Output format matches user expectations
- ⚠️ Speaker context is lost (consecutive lines from same speaker are treated independently)

## Trade-offs

**Benefits:**
- Reliable, predictable translation output
- Clean, readable translation logs
- No risk of corrupted splits

**Limitations:**
- Loss of speaker context across consecutive lines
- Slightly less natural flow when same speaker has multiple consecutive lines
- Potential loss of cross-line context for translation quality

The reliability benefits outweigh the context loss, making this the correct approach.

## Testing

Verified that:
- All unit tests pass
- Line-by-line translation path is used for all .ass files
- Translation logs show individual lines as expected

## Commit

Fixed in commit: `f44a3cf` - "Fix dialogue grouping issue - disable speaker grouping to prevent merged translations"
