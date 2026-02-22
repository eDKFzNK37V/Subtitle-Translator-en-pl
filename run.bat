@echo off
setlocal

set "VENV_DIR=.venv"
set "INSTALL_MARKER=%VENV_DIR%\install.ok"

echo ========================================
echo Subtitle Translator
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Please run install.bat first.
    pause
    exit /b 1
)

REM Activate environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Check if dependencies are installed
if not exist "%INSTALL_MARKER%" (
    echo ERROR: Dependencies not installed.
    echo Please run install.bat first.
    pause
    exit /b 1
)

REM Run the main application (GUI by default)
python main.py

REM Pause to keep the window open after execution
pause
endlocal
