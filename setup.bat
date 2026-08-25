@echo off
chcp 65001 >nul
title Budao Lepao Installer

echo ========================================
echo  Budao Lepao - 一键安装
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 未安装，请先安装 Python 3.10+
    echo 下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
python -c "import sys; v=sys.version_info; exit(0 if v.major>=3 and v.minor>=10 else 1)"
if %errorlevel% neq 0 (
    echo [ERROR] Python 版本过低，需要 3.10+
    pause
    exit /b 1
)

echo [OK] Python %cd%
echo.

:: 安装依赖
echo [1/3] 安装依赖包...
pip install -q numpy opencv-python prettytable fastapi uvicorn pydantic rich pyperclip
if %errorlevel% neq 0 (
    echo [ERROR] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖安装完成
echo.

:: 安装本包
echo [2/3] 安装 budaolepao 命令...
pip install -e . -q
if %errorlevel% neq 0 (
    echo [ERROR] 安装失败
    pause
    exit /b 1
)
echo [OK] 安装完成
echo.

:: 验证
echo [3/3] 验证安装...
budaolepao -h >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] budaolepao 命令未生效，尝试重新打开终端
) else (
    echo [OK] budaolepao 命令可用
)
echo.

echo ========================================
echo  安装完成!
echo ========================================
echo.
echo  使用方法:
echo    budaolepao             开跑
echo    budaolepao dashboard   检测看板
echo    budaolepao map         拾取坐标
echo    budaolepao -h          查看所有命令
echo.
pause