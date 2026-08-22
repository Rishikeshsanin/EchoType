@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo EchoType is not set up yet.
    echo Run setup.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m echotype.app.main
if errorlevel 1 (
    echo.
    echo EchoType exited with an error.
    pause
)
