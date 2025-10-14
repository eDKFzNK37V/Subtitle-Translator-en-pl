# Subtitle Translator (English ↔ Polish, etc.)

A unified, easy-to-use subtitle translation tool supporting `.ass`, `.srt`, and `.txt` formats. Powered by NLLB models (Meta AI) with optional LoRA adapter support for custom fine-tuned models. Includes both a GUI and CLI.

---

## Features

- **Batch translation** with NLLB-200 (1.3B/3.3B) or your own LoRA adapters
- **GUI** (Tkinter) and **CLI** modes
- **Speaker grouping** for `.ass` files
- **Subtitle tag protection** and restoration
- **No file overwrite**: output files are auto-incremented if a name conflict exists
- **Customizable batch size, beam search, and \N tag insertion**
- **Translation log** for every run

---

## Installation

1. **Clone the repository**
2. **Install Python 3.8+**
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # For LoRA support:
   pip install peft
   # For CUDA (optional):
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```
4. **Model auto-download:** The NLLB model will be automatically downloaded from HuggingFace (e.g. `facebook/nllb-200-1.3B` or `facebook/nllb-200-3.3B`) on first launch if not present locally. No manual download required unless you want to use a local/offline copy.

---

## Usage

### GUI

```bash
python main.py
```

- Select your subtitle file
- (Optional) Select a LoRA adapter directory
- Choose source/target language, format, and advanced options
- Click **Start Translation**

### CLI

```bash
python main.py input.ass --src en --tgt pl --batch-size 8 --num-beams 2 --lora-adapter ./outputs/lora_adapter
```

- `--src` / `--tgt`: Language codes (en, pl, ja, fr, de)
- `--lora-adapter`: Path to your LoRA adapter directory (optional)
- `--nwordix`: Word index for \N tag insertion (ASS only)

### Output

- Translated file and log are saved in the same directory as the input.
- If a file exists, a number is appended (e.g. `file_pl_1.ass`).

---

## Custom Model/Adapter

- Place your LoRA adapter in a directory (e.g. `outputs/lora_adapter/`)
- Select it in the GUI or pass `--lora-adapter` in CLI
- The base model (e.g. `facebook/nllb-200-1.3B`) must be available locally or via HuggingFace

---

## Supported Languages

- English (`en`)
- Polish (`pl`)
- Japanese (`ja`)
- French (`fr`)
- German (`de`)

Add more by editing the `LANG_CODES` dictionary in `main.py`.

---

## Troubleshooting

- **Model loading fails:** Check RAM/VRAM, CUDA, and model path
- **peft not installed:** `pip install peft`
- **GUI not launching:** Ensure Tkinter is installed (comes with most Python distributions)
- **Output not appearing:** Check for errors in the terminal/console

---

## License

MIT

---

## Credits

- Meta AI (NLLB)
- HuggingFace Transformers
- PEFT (LoRA)
- tqdm

---

For more details, see `main.py` and `requirements.txt`.
