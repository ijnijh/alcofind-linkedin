@echo off
REM ALCOFIND LinkedIn Composer one-click bootstrap.
REM ASCII only. Bypasses PowerShell execution policy for this one .ps1.
REM Anyone can double-click this from anywhere.

chcp 65001 > nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1"
if errorlevel 1 (
    echo.
    echo [ERR] bootstrap.ps1 failed. See messages above.
    pause
)
