@echo off
setlocal

set "VENV_DIR=.venv"
set "REQ_FILE=requirements.txt"
set "INSTALL_MARKER=%VENV_DIR%\install.ok"

REM Check if the Python virtual environment is already active
IF NOT DEFINED VIRTUAL_ENV (
    REM If .venv does not exist, create it
    IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
        echo Virtual environment not found. Creating %VENV_DIR%...
        python -m venv "%VENV_DIR%"
        if errorlevel 1 goto :EOF
    )
    REM Activate the .venv virtual environment
    call "%VENV_DIR%\Scripts\activate.bat"
) ELSE (
    echo Virtual environment is already active.
)

REM Install dependencies if not installed yet
if exist "%REQ_FILE%" (
    if not exist "%INSTALL_MARKER%" (
        echo Installing dependencies...
        python -m pip install -r "%REQ_FILE%"
        if errorlevel 1 goto :EOF
        echo installed>"%INSTALL_MARKER%"
    )
) else (
    echo Requirements file not found: %REQ_FILE%
)

REM Run the main application (GUI by default)
python main.py

REM Pause to keep the window open after execution
pause
endlocal
