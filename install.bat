@echo off
setlocal

set "VENV_DIR=.venv"
set "REQ_FILE=requirements.txt"
set "INSTALL_MARKER=%VENV_DIR%\install.ok"

echo ========================================
echo Subtitle Translator - Installation
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

echo Python found.

REM Check if venv directory already exists
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo.
    echo Virtual environment already exists.
    set /p "reinstall=Do you want to reinstall? (y/n): "
    if /i not "%reinstall%"=="y" (
        echo Installation cancelled.
        pause
        exit /b 0
    )
    echo Removing existing virtual environment...
    rmdir /s /q "%VENV_DIR%"
)

echo.
echo Creating virtual environment...
python -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo ERROR: Could not create virtual environment
    pause
    exit /b 1
)

echo Virtual environment created successfully.
echo.
echo Installing dependencies...

REM Activate virtual environment and install dependencies
call "%VENV_DIR%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo ERROR: Could not activate virtual environment
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r "%REQ_FILE%"
if %errorlevel% neq 0 (
    echo ERROR: Could not install required packages
    pause
    exit /b 1
)

set "INSTALL_TIMESTAMP=%DATE% %TIME%"
echo installed %INSTALL_TIMESTAMP% > "%INSTALL_MARKER%"

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo Virtual environment created at: %CD%\%VENV_DIR%
echo.
echo To run the translator, use run.bat
echo.
pause
endlocal
