@echo off
cd /d "%~dp0"
title Budao Lepao Installer

echo ========================================
echo  Budao Lepao - One-Click Install
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
python -c "import sys; v=sys.version_info; exit(0 if v.major>=3 and v.minor>=10 else 1)"
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ required.
    pause
    exit /b 1
)
echo [OK] Python
echo.

:: Install deps
echo [1/3] Installing dependencies...
pip install -q numpy opencv-python prettytable fastapi uvicorn pydantic rich pyperclip
if %errorlevel% neq 0 (
    echo [ERROR] Dependency install failed.
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

:: Install package
echo [2/3] Installing budaolepao...
pip install -e . -q
if %errorlevel% neq 0 (
    echo [ERROR] Install failed.
    pause
    exit /b 1
)
echo [OK] Installed
echo.

:: Verify
echo [3/3] Verifying...
where run >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] run not in PATH yet.
    echo Close this window and open a new terminal.
) else (
    echo [OK] run ready
)
echo.

echo ========================================
echo  Install complete!
echo ========================================
echo.
echo  Usage:
echo    run                    run刷跑脚本
echo    run dashboard          detection dashboard
echo    run map                get coordinates
echo    run -h                 all commands
echo.
pause