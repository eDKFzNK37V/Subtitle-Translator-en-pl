# problem_gui.py
import sys
import traceback
import logging, config
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
from logs import SubtitleLogger
from progress_controller import ProgressController
from gui_nllb import run_gui_nllb
 # from gui_m2m100 import run_gui_m2m100
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
            # Model selection popup before main window
            temp_root = tk.Tk()
            temp_root.withdraw()
            selected_engine = tk.StringVar(value=None)

            def show_model_popup():
                popup = tk.Toplevel(temp_root)
                popup.title("Choose Translation Model")
                popup.geometry("400x260")
                popup.grab_set()
                tk.Label(popup, text="Select translation model:", font=("Segoe UI", 12, "bold")).pack(pady=10)

                btn_frame = tk.Frame(popup)
                btn_frame.pack(pady=5)

                def update_buttons():
                    if selected_engine.get() == "nllb":
                        nllb_btn.config(relief="sunken", bg="#d0f0ff")
                        m2m_btn.config(relief="raised", bg=popup.cget('bg'))
                    else:
                        m2m_btn.config(relief="sunken", bg="#d0ffd0")

                def set_engine(engine):
                    selected_engine.set(engine)
                    update_buttons()

                nllb_btn = tk.Button(
                    btn_frame, text="NLLB-200-1.3B", width=18,
                    command=lambda: set_engine("nllb")
                )
                nllb_btn.grid(row=0, column=0, padx=10)
                m2m_btn = tk.Button(
                    btn_frame, text="M2M100", width=18,
                    command=lambda: set_engine("m2m100")
                )
                m2m_btn.grid(row=0, column=1, padx=10)

                # Pros/cons labels
                pros_frame = tk.Frame(popup)
                pros_frame.pack(pady=5)
                nllb_pros = tk.Label(
                    pros_frame,
                    text="+ Best quality\n+ Handles rare languages\n- Slow\n- Needs good GPU",
                    justify="left", fg="#005080"
                )
                nllb_pros.grid(row=0, column=0, padx=10, sticky="w")
                m2m_pros = tk.Label(
                    pros_frame,
                    text="+ Fast\n+ Lower RAM\n- Lower quality\n- Fewer languages",
                    justify="left", fg="#005020"
                )
                m2m_pros.grid(row=0, column=1, padx=10, sticky="w")
                update_buttons()

                def accept():
                    popup.destroy()

                accept_btn = tk.Button(popup, text="Accept", width=12, command=accept)
                accept_btn.pack(pady=15)

                popup.wait_window()
               
            show_model_popup()
            config.selected_engine = selected_engine.get()  # <-- set the global indicator
            temp_root.destroy()
            # Import and launch the appropriate GUI only after user selection
            if config.selected_engine == "nllb":
                from gui_nllb import run_gui_nllb
                run_gui_nllb()
                print("NLLB GUI launched")
            elif config.selected_engine == "m2m100":
                from gui_m2m100 import run_gui_m2m100
                run_gui_m2m100()
                print("M2M100 GUI launched")