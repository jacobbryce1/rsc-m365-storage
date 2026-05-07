@echo off
REM ============================================================
REM  RSC M365 Storage Report - Deployment Script (Windows)
REM ============================================================
REM  Sets up the Python virtual environment and installs
REM  dependencies. Run once after extracting the project.
REM
REM  Usage: Double-click deploy.bat  OR  run from Command Prompt
REM ============================================================

echo ============================================================
echo   RSC M365 Storage Report - Deployment
echo ============================================================
echo.

REM ── Python check ─────────────────────────────────────────────
echo Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo   Download from: https://www.python.org/downloads/
    echo   During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VERSION=%%i
echo   Found: %PY_VERSION%

REM ── Virtual environment ───────────────────────────────────────
echo.
echo Creating virtual environment...
if exist venv (
    echo   Removing existing venv...
    rmdir /s /q venv
)
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
    echo        Ensure python3-venv is available: python -m ensurepip
    pause
    exit /b 1
)
echo   Virtual environment created

REM ── Dependencies ─────────────────────────────────────────────
echo.
echo Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Dependency installation failed.
    echo        Check your network connection and try again.
    pause
    exit /b 1
)
echo   Dependencies installed

REM ── .env setup ───────────────────────────────────────────────
echo.
if not exist .env (
    echo Creating .env from template...
    copy .env.example .env >nul
    echo   .env created
    echo.
    echo   ======================================================
    echo   ACTION REQUIRED: Edit .env with your RSC credentials
    echo.
    echo     notepad .env
    echo   ======================================================
) else (
    echo   .env already exists ^(not overwritten^)
)

echo.
echo ============================================================
echo   Deployment complete!
echo.
echo   Next steps:
echo     1. Edit .env with your RSC credentials ^(notepad .env^)
echo     2. python run_report.py
echo ============================================================
echo.
pause