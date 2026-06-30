@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =====================================
echo   WeixinProxyBridge Startup Script
echo =====================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found:
python --version

REM Create venv if not exists
if not exist venv\ (
    echo.
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo [OK] venv created
)

REM Activate venv
echo.
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate venv
    pause
    exit /b 1
)
echo [OK] venv activated

REM Install requirements
echo.
echo [SETUP] Installing dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies. Trying without --quiet...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)
echo [OK] Dependencies installed

REM Start server
echo.
echo [START] Launching bridge service...
echo.
python server.py

pause
