@echo off
REM Check if the Python virtual environment is already active
IF NOT DEFINED VIRTUAL_ENV (
    REM If .venv does not exist, create it
    IF NOT EXIST ".venv\Scripts\activate.bat" (
        echo Virtual environment not found. Creating .venv...
        python -m venv .venv
    )
    REM Activate the .venv virtual environment
    call .venv\Scripts\activate.bat
) ELSE (
    echo Virtual environment is already active.
)

REM Run the main application (GUI by default)
python main.py

REM Pause to keep the window open after execution
pause
