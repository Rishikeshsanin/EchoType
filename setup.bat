@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ================================================================
echo   EchoType v0.9.0 Beta - Windows setup
echo ================================================================
echo.

set "PY="
for %%V in (3.12 3.11) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1
        if !errorlevel! equ 0 set "PY=py -%%V"
    )
)

if not defined PY (
    echo   [FAIL] EchoType currently supports Python 3.11 or 3.12.
    echo          Install Python 3.12 and run this file again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%G in ('%PY% -c "import sys;print(sys.version.split()[0])"') do set "PYVER=%%G"
echo   [ok] Python !PYVER!

if not exist ".venv\Scripts\python.exe" (
    echo   [..] Creating virtual environment
    %PY% -m venv .venv
    if errorlevel 1 goto :fail
)

set "VPY=.venv\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip --quiet --disable-pip-version-check
if errorlevel 1 goto :fail

echo.
echo   Detecting compute device...
set "HASGPU="
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 set "HASGPU=1"

if defined HASGPU (
    for /f "tokens=*" %%G in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do echo   [ok] Found %%G
    echo   [..] Installing tested PyTorch 2.6.0 CUDA 12.4 build
    "%VPY%" -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124 --disable-pip-version-check
    if errorlevel 1 (
        echo   [warn] CUDA build failed; falling back to CPU PyTorch
        "%VPY%" -m pip install torch==2.6.0 --disable-pip-version-check
    )
) else (
    echo   [ok] No NVIDIA GPU detected; installing CPU PyTorch
    "%VPY%" -m pip install torch==2.6.0 --disable-pip-version-check
)
if errorlevel 1 goto :fail

echo.
echo   [..] Installing EchoType and speech dependencies
"%VPY%" -m pip install -e . --disable-pip-version-check
if errorlevel 1 goto :fail

echo.
echo   [..] Running EchoType verification
"%VPY%" verify.py
if errorlevel 1 goto :fail

echo.
echo ================================================================
echo   Setup complete.
echo   Start EchoType with run.bat
echo ================================================================
echo.
pause
exit /b 0

:fail
echo.
echo   [FAIL] EchoType setup did not complete. Review the error above.
echo.
pause
exit /b 1
