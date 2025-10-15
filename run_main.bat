
@echo off
REM Run the Subtitle Translator main script using the local Python environment

REM Activate virtual environment if it exists
IF EXIST "subtitle-env\Scripts\activate.bat" (
	call subtitle-env\Scripts\activate.bat
)

REM Run the main application (GUI by default)
python main.py

REM Pause to keep the window open after execution
pause

