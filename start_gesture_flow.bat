@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title Gesture Flow - Touchless HCI Controller
cd /d "%~dp0"

echo ========================================================
echo   Starting Gesture Flow Native Vision Controller
echo ========================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    uv run python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Gesture Flow stopped with code %ERRORLEVEL%.
    pause
)
