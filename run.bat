@echo off
title Nexus Gesture Controller
set PYTHONDONTWRITEBYTECODE=1
echo ========================================================
echo         Launching Nexus Gesture Controller
echo ========================================================
cd backend
py -3.12 -B main.py 2>nul
if errorlevel 1 (
    python -B main.py
)
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to run. Make sure dependencies are installed:
    echo Please run 'install_dependencies.bat' first!
    pause
)
