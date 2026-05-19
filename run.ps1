# ALCOFIND LinkedIn 작성앱 실행 스크립트 (Windows PowerShell)
# 사용: 우클릭 → PowerShell에서 실행, 또는 PowerShell에서 .\run.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = "C:\Users\jhkim\AppData\Local\Programs\Python\Python312\python.exe"
$venv = Join-Path $PSScriptRoot ".venv"

if (-not (Test-Path $venv)) {
    Write-Host ">> venv 없음 — 생성 후 의존성 설치합니다..." -ForegroundColor Yellow
    & $python -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

Write-Host ">> Streamlit 앱을 기동합니다. 브라우저가 자동으로 열립니다." -ForegroundColor Green
& .\.venv\Scripts\python.exe -m streamlit run app.py
