# ALCOFIND LinkedIn Composer - Streamlit watchdog
# Monitors port 8501 health every 30 seconds.
# If Streamlit is not responding, restarts run.bat in a new cmd window.
# Ascii-only by design (PS 5.1 + cp949 console safety).

$ErrorActionPreference = "SilentlyContinue"
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunBat      = Join-Path $ScriptDir "run.bat"
$Port        = 8501
$HealthUrl   = "http://localhost:$Port/_stcore/health"
$CheckEvery  = 30   # seconds between checks
$Cooldown    = 60   # min seconds between restarts (avoid restart loop)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " ALCOFIND Watchdog - port $Port monitor" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Health check every $CheckEvery seconds."
Write-Host "Close this window to stop monitoring."
Write-Host ""

$lastRestart = (Get-Date).AddMinutes(-10)
$consecutiveDown = 0

while ($true) {
    $ts = (Get-Date).ToString("HH:mm:ss")
    $alive = $false
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $alive = $true }
    } catch {}

    if ($alive) {
        if ($consecutiveDown -gt 0) {
            Write-Host "$ts [OK]      Streamlit recovered" -ForegroundColor Green
        } else {
            Write-Host "$ts [OK]      responding" -ForegroundColor DarkGray
        }
        $consecutiveDown = 0
    } else {
        $consecutiveDown += 1
        $sinceLast = ((Get-Date) - $lastRestart).TotalSeconds
        if ($sinceLast -lt $Cooldown) {
            $wait = [int]($Cooldown - $sinceLast)
            Write-Host "$ts [WAIT]    not responding (cooldown ${wait}s)" -ForegroundColor Yellow
        } else {
            Write-Host "$ts [RESTART] Streamlit down - restarting..." -ForegroundColor Red
            try {
                Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | ForEach-Object {
                    try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
                }
            } catch {}
            Start-Sleep -Seconds 2
            if (Test-Path $RunBat) {
                Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "`"$RunBat`""
                Write-Host "$ts [LAUNCH]  run.bat in new cmd window" -ForegroundColor Cyan
            } else {
                Write-Host "$ts [ERR]     run.bat missing at $RunBat" -ForegroundColor Red
            }
            $lastRestart = Get-Date
        }
    }
    Start-Sleep -Seconds $CheckEvery
}
