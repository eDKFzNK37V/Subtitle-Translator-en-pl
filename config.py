import os
import re
import torch
import pysubs2
import language_tool_python
from functools import lru_cache
import tkinter as tk
from tkinter import filedialog, messagebox
from tqdm import tqdm
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    pipeline,
    AutoModelForTokenClassification
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
selected_engine = "nllb"  # Default and only supported engine
