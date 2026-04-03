# HomerFindr — Windows Installer
# Usage: irm https://raw.githubusercontent.com/iamtr0n/HomerFindr/main/install.ps1 | iex
# Or run directly: .\install.ps1

$ErrorActionPreference = "Stop"
$REPO = "https://github.com/iamtr0n/HomerFindr.git"
$INSTALL_DIR = "$env:LOCALAPPDATA\HomerFindr"
$TASK_NAME = "HomerFindr"

function Write-Step($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "  🏠  HomerFindr Installer" -ForegroundColor White
Write-Host "  ─────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# ── Helper: install via winget ────────────────────────────────────────────────
function Install-Via-Winget($id, $name) {
    Write-Step "Installing $name via winget..."
    winget install --id $id --silent --accept-package-agreements --accept-source-agreements
    # Refresh PATH for this session
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User")
}

# ── 1. Python 3.11+ ───────────────────────────────────────────────────────────
Write-Step "Checking Python..."
$PYTHON_BIN = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd -c "import sys; print(sys.version_info >= (3,11))" 2>$null
        if ($ver -eq "True") {
            $PYTHON_BIN = $cmd
            $pyver = & $cmd --version 2>&1
            Write-OK "Python $pyver found"
            break
        }
    } catch {}
}

if (-not $PYTHON_BIN) {
    Write-Warn "Python 3.11+ not found"
    $answer = Read-Host "  Install Python 3.11 automatically via winget? (y/n)"
    if ($answer -match "^[Yy]") {
        Install-Via-Winget "Python.Python.3.11" "Python 3.11"
        $PYTHON_BIN = "python"
        Write-OK "Python 3.11 installed"
    } else {
        Write-Err "Python 3.11+ required. Download from https://www.python.org/downloads/"
        exit 1
    }
}

# ── 2. Node.js ────────────────────────────────────────────────────────────────
Write-Step "Checking Node.js..."
try {
    $nodever = node --version 2>&1
    Write-OK "Node.js $nodever found"
} catch {
    Write-Warn "Node.js not found"
    $answer = Read-Host "  Install Node.js automatically via winget? (y/n)"
    if ($answer -match "^[Yy]") {
        Install-Via-Winget "OpenJS.NodeJS.LTS" "Node.js LTS"
        Write-OK "Node.js installed"
    } else {
        Write-Err "Node.js required. Download from https://nodejs.org/"
        exit 1
    }
}

# ── 3. Git ────────────────────────────────────────────────────────────────────
Write-Step "Checking Git..."
try {
    $gitver = git --version 2>&1
    Write-OK "$gitver found"
} catch {
    Write-Warn "Git not found"
    $answer = Read-Host "  Install Git automatically via winget? (y/n)"
    if ($answer -match "^[Yy]") {
        Install-Via-Winget "Git.Git" "Git"
        Write-OK "Git installed"
    } else {
        Write-Err "Git required. Download from https://git-scm.com/"
        exit 1
    }
}

Write-Host ""
Write-Host "  All dependencies satisfied — installing HomerFindr..." -ForegroundColor White
Write-Host ""

# ── 4. Clone or update ────────────────────────────────────────────────────────
if (Test-Path "$INSTALL_DIR\.git") {
    Write-Step "Updating existing install..."
    git -C $INSTALL_DIR pull --quiet
} else {
    Write-Step "Downloading HomerFindr..."
    git clone --quiet $REPO $INSTALL_DIR
}

Set-Location $INSTALL_DIR

# ── 5. Python venv + install ──────────────────────────────────────────────────
Write-Step "Installing Python dependencies..."
& $PYTHON_BIN -m venv .venv --quiet
.venv\Scripts\pip install -e . --quiet

# ── 6. Build frontend ─────────────────────────────────────────────────────────
Write-Step "Building web dashboard..."
Set-Location frontend
npm install --silent
npm run build --silent
Set-Location $INSTALL_DIR

# ── 7. Create .env if missing ─────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

# ── 8. Windows Task Scheduler (auto-start at login) ──────────────────────────
Write-Step "Setting up auto-start..."

$homesearchBin = "$INSTALL_DIR\.venv\Scripts\homesearch.exe"
$action = New-ScheduledTaskAction -Execute $homesearchBin -Argument "serve" -WorkingDirectory $INSTALL_DIR
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive

# Remove old task if exists
Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $TASK_NAME -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
Write-OK "Auto-start registered (runs at login)"

# ── 9. Desktop shortcut ───────────────────────────────────────────────────────
$WS = New-Object -ComObject WScript.Shell
$shortcut = $WS.CreateShortcut("$env:USERPROFILE\Desktop\HomerFindr.lnk")
$shortcut.TargetPath = $homesearchBin
$shortcut.Arguments = "serve"
$shortcut.WorkingDirectory = $INSTALL_DIR
$shortcut.Description = "HomerFindr — Home Search Aggregator"
$shortcut.Save()
Write-OK "Desktop shortcut created"

# ── 10. Start now ─────────────────────────────────────────────────────────────
Write-Step "Starting HomerFindr..."
Start-Process -FilePath $homesearchBin -ArgumentList "serve" -WorkingDirectory $INSTALL_DIR -WindowStyle Minimized

# Wait for server
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep 1
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/searches" -UseBasicParsing -TimeoutSec 1
        $ready = $true
        break
    } catch {}
}

Write-Host ""
if ($ready) {
    Write-OK "HomerFindr is running!"
} else {
    Write-Warn "Server may still be starting — give it a few seconds"
}
Write-Host ""
Write-Host "  → Open in browser:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  → CLI search:       homerfindr" -ForegroundColor Cyan
Write-Host "  → Stop:             Stop-ScheduledTask -TaskName HomerFindr" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  HomerFindr will auto-start every time you log in." -ForegroundColor DarkGray
Write-Host ""

# Open browser
Start-Process "http://127.0.0.1:8000"

# ── Optional: SMS alerts ───────────────────────────────────────────────────────
Write-Host "  ─────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  📱  Want SMS alerts when new homes hit?" -ForegroundColor White
Write-Host "     Free Zapier account — takes 3 minutes." -ForegroundColor DarkGray
Write-Host "  ─────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
$sms = Read-Host "  Set up SMS alerts now? (y/n)"

if ($sms -match "^[Yy]") {
    $phone = Read-Host "  Your phone number (e.g. +12125551234)"
    Write-Host ""
    Write-Host "  Step 1 — Go to https://zapier.com/sign-up (free, no credit card)" -ForegroundColor Cyan
    Write-Host "  Step 2 — Click Create → New Zap" -ForegroundColor Cyan
    Write-Host "  Step 3 — Paste this prompt into Zapier's AI box:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  ┌──────────────────────────────────────────────────────────────┐" -ForegroundColor DarkGray
    Write-Host "  Create and publish a Zap:" -ForegroundColor White
    Write-Host ""
    Write-Host "  1. Trigger: Webhooks by Zapier - Catch Hook (JSON)" -ForegroundColor White
    Write-Host "  2. Action: SMS by Zapier - Send SMS" -ForegroundColor White
    Write-Host "     - To: $phone" -ForegroundColor White
    Write-Host "     - From: 650-646-9270 (fixed, not random)" -ForegroundColor White
    Write-Host "     - Message: Map the 'message' field directly from the webhook" -ForegroundColor White
    Write-Host ""
    Write-Host "  Map: webhook message field -> SMS message body" -ForegroundColor White
    Write-Host "  Authentication: SMS by Zapier account" -ForegroundColor White
    Write-Host "  Name: HomerFindr SMS Alert" -ForegroundColor White
    Write-Host "  Then publish it." -ForegroundColor White
    Write-Host "  └──────────────────────────────────────────────────────────────┘" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Step 4 — Copy the Catch Hook URL Zapier gives you, paste it below:" -ForegroundColor Cyan
    Write-Host ""
    $webhook = Read-Host "  Zapier webhook URL"
    if ($webhook) {
        Add-Content ".env" "`nZAPIER_WEBHOOK_URL=$webhook"
        Write-OK "Webhook saved. Restart HomerFindr to apply."
    }
}

Write-Host ""
Write-Host "  HomerFindr setup complete. Happy house hunting! 🏠" -ForegroundColor Green
Write-Host ""
