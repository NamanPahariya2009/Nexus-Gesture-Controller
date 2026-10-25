@echo off
title Install Dependencies - Nexus Gesture Controller
echo ========================================================
echo   Installing Dependencies for Nexus Gesture Controller
echo ========================================================
cd backend
py -3.12 -m pip install -r requirements.txt 2>nul
if errorlevel 1 (
    python -m pip install -r requirements.txt
)
echo.
echo ========================================================
echo All dependencies installed! You can now run 'run.bat'.
echo ========================================================
pause
