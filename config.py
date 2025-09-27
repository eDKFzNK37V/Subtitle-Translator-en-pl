import torch
import warnings
warnings.filterwarnings("ignore", message="`resume_download` is deprecated and will be removed in version 1.0.0")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
selected_engine = "nllb"  # Default and only supported engine
