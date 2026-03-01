@echo off
echo Starting Grimoire...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

:: Install dependencies
echo Installing/Updating dependencies...
pip install -r requirements.txt

:: Run the application
echo Launching Grimoire on http://localhost:8080
python app.py

pause
