@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title Gesture Flow - Touchless HCI Controller

echo ========================================================
echo   Starting Gesture Flow Native Vision Controller
echo ========================================================

:: 1. Detect project directory
set "PROJECT_DIR=%~dp0"

if not exist "%PROJECT_DIR%main.py" (
    if exist "D:\Gesture Flow\Gesture Flow\main.py" (
        set "PROJECT_DIR=D:\Gesture Flow\Gesture Flow\"
    ) else if exist "D:\Gesture Flow\main.py" (
        set "PROJECT_DIR=D:\Gesture Flow\"
    )
)

cd /d "%PROJECT_DIR%"
echo [Info] Working Directory: %CD%

:: 2. Launch with project virtual environment
if exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    "%PROJECT_DIR%.venv\Scripts\python.exe" "%PROJECT_DIR%main.py"
) else (
    uv run python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Gesture Flow stopped with code %ERRORLEVEL%.
    pause
)
