@echo off
setlocal enabledelayedexpansion

:: FICE — Personal Finance Tracker Launcher (Windows)
:: Usage: fice.bat [dev|test]
::   (no args)  Launch the native desktop window.
::   dev         Start in dev mode (browser at http://127.0.0.1:8000).
::   test        Run the test suite.

cd /d "%~dp0"

:: ---- Python version check ----
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 3.11+ is required.
    echo Install it from https://www.python.org/downloads/
    exit /b 1
)

:: ---- WebView2 check (Windows 10/11 has it built-in) ----
:: pywebview uses Edge WebView2. If missing, the app shows a clear error.
:: Pre-installed on Windows 10 (with Edge) and Windows 11.
:: Manual install: https://developer.microsoft.com/microsoft-edge/webview2/

:: ---- Virtual environment ----
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        exit /b 1
    )
)

call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    exit /b 1
)

echo Installing dependencies...
pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)

:: ---- Dispatch ----
set "MODE=%~1"
if "%MODE%"=="" set "MODE=run"

if /i "%MODE%"=="dev" (
    echo Starting in dev mode → http://127.0.0.1:8000
    uvicorn app:create_app --reload --factory
) else if /i "%MODE%"=="test" (
    python -m pytest tests/ -v
) else if /i "%MODE%"=="run" (
    python main.py
) else (
    echo Unknown mode: %MODE%
    echo Usage: fice.bat [dev^|test]
    exit /b 1
)
