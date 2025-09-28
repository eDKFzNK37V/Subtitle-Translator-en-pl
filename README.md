# English-to-Polish Subtitle Translator

This repository provides tools for **translating English subtitles to Polish** and **correcting Polish subtitles**. It supports `.ass`, `.srt`, and `.txt` file formats, with plans to expand support for additional formats in the future.

## Features

- **Subtitle Translation**: Translate English subtitles into Polish using advanced neural models.
- **Subtitle Correction**: Correct grammar, spelling, and style in Polish subtitles.
- **Context-Aware Processing**: Handles subtitle tags and dialogue grouping intelligently.
- **Batch Processing**: Process multiple subtitle files efficiently.
- **User-Friendly Interface**: Includes both a Command-Line Interface (CLI) and a Graphical User Interface (GUI).

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/eDKFzNK37V/Subtitle-Translator-en-pl.git
   cd Subtitle-Translator-en-pl
   ```
2. Set up the Python environment:
   ```bash
   python -m venv subtitle-env
   subtitle-env\Scripts\activate  # On Windows
   pip install -r requirements.txt
   ```
3. (Optional) Test if there is CUDA support-CUDA cores boosts the processing:
   ```bash
   python CUDA-TEST.py
   ```

## Usage

### Command-Line Interface (CLI)

```bash
python main.py
```

To translate a subtitle file from the command line:

```bash
python main.py <input_file> [--src en|pl] [--tgt en|pl]
```

Examples:

```bash
python main.py example.ass
python main.py example.ass --src en --tgt pl
python main.py example.ass --src pl --tgt en
```

If you are not sure, just run:

```bash
python main.py
```

### Graphical User Interface (GUI)

Launch the GUI:

```bash
python main_gui.py
```

## Examples

### Input

**File**: `example.ass`

```
1
00:00:01,000 --> 00:00:04,000
Hello, world!
```

### Output

**Translated File**: `example_translated.ass`

```
1
00:00:01,000 --> 00:00:04,000
Cześć, świecie!
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a clear description of your changes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

### CLI Callbacks and Logging

The CLI now includes comprehensive callback and logging functionality for monitoring translation events:

### CLI Event Types
- **start**: Translation begins
- **progress**: Translation progress updates
- **finish**: Translation completes successfully  
- **error**: Translation encounters an error

### Automatic Logging
The CLI automatically:
- Creates detailed logs for each translation session
- Tracks timing, progress, and any errors
- Saves logs in the same directory as the output file
- Provides console feedback with progress indicators

### Custom Callbacks
You can register custom callbacks to handle CLI events:

```python
from cli_callbacks import register_cli_callback, CLIEventData

def my_callback(event_data: CLIEventData):
    print(f"Event: {event_data.event_type}")
    print(f"File: {event_data.input_file}")
    if event_data.progress:
        current, total = event_data.progress
        print(f"Progress: {current}/{total}")

register_cli_callback('on_progress', my_callback)
```

### Event Data Structure
Each callback receives a `CLIEventData` object containing:
- `event_type`: The type of event (start, progress, finish, error)
- `input_file`: Path to the input subtitle file
- `output_file`: Path to the output file (when available)
- `src_lang`, `tgt_lang`: Source and target language codes
- `status`: Current processing status
- `error_msg`: Error message (for error events)
- `progress`: Tuple of (current, total) for progress events
- `log_path`: Path to the log file (when available)
- `timestamp`: When the event occurred

## Help

The following usage instructions are available for the application:

To use the GUI (recommended for most users):
