@echo off
REM ALCOFIND LinkedIn Composer launcher.
REM ASCII-only by design - Korean characters can break cmd parsing under default OEM code page.
REM Sets UTF-8 console code page (65001) so that Python/Streamlit output renders Korean correctly.

chcp 65001 > nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PYTHON=C:\Users\jhkim\AppData\Local\Programs\Python\Python312\python.exe"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"

REM --- Move to script directory robustly ---
pushd "%SCRIPT_DIR%" 1>nul 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to change directory to: %SCRIPT_DIR%
    pause
    exit /b 1
)

REM --- Verify base Python exists ---
if not exist "%PYTHON%" (
    echo [ERROR] Python 3.12 not found at:
    echo         %PYTHON%
    echo Install Python 3.12 first or update PYTHON path in this file.
    popd
    pause
    exit /b 1
)

REM --- Create venv if missing ---
if not exist "%VENV_PY%" (
    echo.
    echo [SETUP] Creating venv and installing dependencies...
    "%PYTHON%" -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv creation failed.
        popd
        pause
        exit /b 1
    )
    "%VENV_PY%" -m pip install --upgrade pip
    "%VENV_PY%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 (
        echo [ERROR] pip install failed.
        popd
        pause
        exit /b 1
    )
)

REM --- Verify requirements.txt exists ---
if not exist "%SCRIPT_DIR%requirements.txt" (
    echo [ERROR] requirements.txt not found at: %SCRIPT_DIR%requirements.txt
    popd
    pause
    exit /b 1
)

REM --- Verify app.py exists ---
if not exist "%SCRIPT_DIR%app.py" (
    echo [ERROR] app.py not found at: %SCRIPT_DIR%app.py
    popd
    pause
    exit /b 1
)

echo.
echo [RUN] Starting Streamlit. Browser opens automatically at http://localhost:8501
echo       To stop: press Ctrl+C in this window.
echo.

"%VENV_PY%" -m streamlit run "%SCRIPT_DIR%app.py"

popd
endlocal
