# ALCOFIND LinkedIn Composer - one-click bootstrap.
# ASCII-only by design: Windows PowerShell 5.1 misreads UTF-8 without BOM,
# so Korean characters in messages would corrupt parsing.
# Behavior:
#   1) Reuse key from .env if present
#   2) Otherwise auto-detect Anthropic API key from clipboard
#   3) Otherwise show a GUI input box
#   4) Free port 8501 if occupied
#   5) Launch run.bat in a new cmd window
#   6) When Streamlit answers, open the browser

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile   = Join-Path $ScriptDir ".env"
$RunBat    = Join-Path $ScriptDir "run.bat"
$Port      = 8501
$AppUrl    = "http://localhost:$Port"

function W-Info ($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function W-OK   ($m) { Write-Host "[OK]   $m" -ForegroundColor Green }
function W-Warn ($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function W-Err  ($m) { Write-Host "[ERR]  $m" -ForegroundColor Red }

function Test-KeyFormat ($k) {
    if (-not $k) { return $false }
    return ($k -match '^sk-ant-api\S+$')
}

function Show-KeyDialog {
    # Windows Forms TopMost dialog - guaranteed to appear in front
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "ALCOFIND Setup - Anthropic API Key"
    $form.Size = New-Object System.Drawing.Size(560, 200)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true
    $form.ShowInTaskbar = $true

    $label = New-Object System.Windows.Forms.Label
    $label.Text = "Paste your Anthropic API key (starts with sk-ant-api):"
    $label.Location = New-Object System.Drawing.Point(15, 20)
    $label.Size = New-Object System.Drawing.Size(520, 22)
    $form.Controls.Add($label)

    $textBox = New-Object System.Windows.Forms.TextBox
    $textBox.Location = New-Object System.Drawing.Point(15, 50)
    $textBox.Size = New-Object System.Drawing.Size(520, 24)
    $textBox.UseSystemPasswordChar = $true
    $form.Controls.Add($textBox)

    $hint = New-Object System.Windows.Forms.Label
    $hint.Text = "Get a key at: https://console.anthropic.com/settings/keys"
    $hint.Location = New-Object System.Drawing.Point(15, 80)
    $hint.Size = New-Object System.Drawing.Size(520, 22)
    $hint.ForeColor = [System.Drawing.Color]::Gray
    $form.Controls.Add($hint)

    $okBtn = New-Object System.Windows.Forms.Button
    $okBtn.Text = "OK"
    $okBtn.Location = New-Object System.Drawing.Point(355, 120)
    $okBtn.Size = New-Object System.Drawing.Size(85, 28)
    $okBtn.DialogResult = "OK"
    $form.Controls.Add($okBtn)
    $form.AcceptButton = $okBtn

    $cancelBtn = New-Object System.Windows.Forms.Button
    $cancelBtn.Text = "Cancel"
    $cancelBtn.Location = New-Object System.Drawing.Point(450, 120)
    $cancelBtn.Size = New-Object System.Drawing.Size(85, 28)
    $cancelBtn.DialogResult = "Cancel"
    $form.Controls.Add($cancelBtn)
    $form.CancelButton = $cancelBtn

    # Force focus to top
    $form.Add_Shown({
        $form.TopMost = $true
        $form.Activate()
        $textBox.Focus() | Out-Null
    })

    $result = $form.ShowDialog()
    $value = ""
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        $value = $textBox.Text
    }
    $form.Dispose()
    return $value
}

function Get-KeyFromUser {
    # 1) Try clipboard
    try {
        $c = (Get-Clipboard -ErrorAction Stop)
        if ($c) { $c = $c.Trim() }
        if (Test-KeyFormat $c) {
            W-OK "Found Anthropic API key in clipboard."
            return $c
        }
    } catch {}

    # 2) TopMost Windows Forms dialog
    W-Info "No API key in clipboard. Opening input dialog (front)..."
    $k = Show-KeyDialog
    if ($k) { $k = $k.Trim() }
    if (-not (Test-KeyFormat $k)) {
        W-Err "Not a valid Anthropic API key (must start with sk-ant-api)."
        Write-Host ""
        Write-Host "Get a key at https://console.anthropic.com/settings/keys and try again." -ForegroundColor Yellow
        Read-Host "Press Enter to close"
        exit 1
    }
    return $k
}

# ---------------- main ----------------

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " ALCOFIND LinkedIn Composer - auto start" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 1) Read existing .env
$existing = ""
if (Test-Path $EnvFile) {
    $content = Get-Content $EnvFile -Raw -ErrorAction SilentlyContinue
    if ($content -match 'ANTHROPIC_API_KEY=(sk-ant-api\S+)') {
        $existing = $Matches[1]
    }
}

if ($existing) {
    $tail = $existing.Substring([Math]::Max(0, $existing.Length - 8))
    W-Info "Existing API key found in .env (...$tail) - reusing"
    $apiKey = $existing
} else {
    W-Info "No API key in .env - need to set up"
    $apiKey = Get-KeyFromUser
    Set-Content -Path $EnvFile -Value "ANTHROPIC_API_KEY=$apiKey" -Encoding UTF8 -NoNewline
    W-OK ".env written"
}

# 2) Free port 8501 if occupied
try {
    $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($c in $conns) {
            try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
        }
        W-Info "Stopped previous process on port $Port"
        Start-Sleep -Seconds 2
    }
} catch {}

# 3) Validate run.bat
if (-not (Test-Path $RunBat)) {
    W-Err "run.bat not found: $RunBat"
    Read-Host "Press Enter to close"
    exit 1
}

# 4) Launch Streamlit in new cmd window
W-Info "Starting Streamlit in a new window..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "`"$RunBat`""

# 5) Wait for server (up to 90 seconds - first run includes venv install)
W-Info "Waiting for Streamlit to respond..."
$deadline = (Get-Date).AddSeconds(90)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri "$AppUrl/_stcore/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
    Write-Host "." -NoNewline
}
Write-Host ""

if ($ready) {
    W-OK "Streamlit ready - opening browser"
    Start-Process $AppUrl
} else {
    W-Warn "Server did not respond within 90 seconds."
    Write-Host "    Check the new cmd window for messages," -ForegroundColor Yellow
    Write-Host "    then open $AppUrl manually in a moment." -ForegroundColor Yellow
}


# 6) Start watchdog in a separate PowerShell window (auto-restart if Streamlit dies)
$Watchdog = Join-Path $ScriptDir "watchdog.ps1"
if (Test-Path $Watchdog) {
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Watchdog
    )
    W-OK "Watchdog started - auto-restart on disconnect (separate window)"
} else {
    W-Warn "watchdog.ps1 not found - manual restart needed if app dies"
}

Write-Host ""
W-OK "Done. You can close this window. Streamlit + Watchdog run in their own windows."
Write-Host ""
Start-Sleep -Seconds 3
