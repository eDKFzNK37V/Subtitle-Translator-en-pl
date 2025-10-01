# Installation Guide

## System Requirements

- **Python**: 3.11 or higher
- **Operating System**: Linux, Windows, or macOS
- **GPU** (recommended): NVIDIA GPU with CUDA 12.1 support
- **RAM**: At least 8GB (16GB recommended)
- **Disk Space**: ~15GB for model and dependencies

## Step-by-Step Installation

### 1. Install Python 3.11+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv
```

**macOS (using Homebrew):**
```bash
brew install python@3.11
```

**Windows:**
Download and install from [python.org](https://www.python.org/downloads/)

### 2. Clone the Repository

```bash
git clone https://github.com/eDKFzNK37V/NLLB-3.3-test.git
cd NLLB-3.3-test
```

### 3. Create Virtual Environment (Recommended)

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies

**With CUDA 12.1 (GPU acceleration):**
```bash
pip install -r requirements.txt
```

**For CPU-only (no CUDA):**
```bash
pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu
pip install transformers sentencepiece protobuf tqdm
```

**For different CUDA versions:**
- CUDA 11.8: Replace `cu121` with `cu118` in requirements.txt
- Check [PyTorch website](https://pytorch.org/get-started/locally/) for other versions

### 5. Verify Installation

Check Python version:
```bash
python --version  # Should show 3.11+
```

Test the script:
```bash
python translate_ass.py --help
```

### 6. First Run (Model Download)

On first use, the NLLB-3.3B model (~13GB) will be downloaded automatically:
```bash
python translate_ass.py example.ass output.ass eng fra
```

This may take 10-30 minutes depending on your internet speed. The model is cached for future use.

## Troubleshooting

### "No module named 'torch'"
```bash
pip install --upgrade -r requirements.txt
```

### CUDA Version Mismatch
Check your CUDA version:
```bash
nvidia-smi  # Look for "CUDA Version"
```

Install matching PyTorch version from [pytorch.org](https://pytorch.org/)

### Out of Memory Errors
- Use CPU mode: `--device cpu`
- Close other applications
- Use a smaller model if available

### Slow Translation (CPU mode)
- Translation on CPU is significantly slower (~10-30x)
- Consider using a GPU or cloud service with GPU
- Process smaller batches

## Upgrading

To upgrade to the latest version:
```bash
git pull origin main
pip install --upgrade -r requirements.txt
```

## Uninstallation

```bash
# Remove virtual environment
deactivate
rm -rf venv

# Remove repository
cd ..
rm -rf NLLB-3.3-test
```

## Additional Resources

- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)
- [NLLB Model Card](https://huggingface.co/facebook/nllb-200-3.3B)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers/)
