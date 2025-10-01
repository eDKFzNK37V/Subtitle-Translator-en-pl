# problem_gui.py
import sys
import traceback
import logging, config
from tkinter import messagebox
logging.basicConfig(filename="error.log", level=logging.ERROR)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    detailed_message = (
        f"\n[ERROR] {exc_type.__name__}: {exc_value}\n"
        f"Traceback:\n{tb_str}"
    )
    logging.error(detailed_message)
    messagebox.showerror(
        "Unexpected Error",
        f"{exc_type.__name__}: {exc_value}\n\n"
        "See error.log for full details."
    )


sys.excepthook = handle_exception


def run_gui():
    # Set NLLB as the default and only engine
    config.selected_engine = "nllb"
    # Launch NLLB GUI directly
    from gui_nllb import run_gui_nllb
    run_gui_nllb()
    print("NLLB GUI launched")