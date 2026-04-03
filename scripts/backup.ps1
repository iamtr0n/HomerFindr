# HomerFindr — Windows Backup & Restore
# Usage:
#   .\scripts\backup.ps1           # create backup
#   .\scripts\backup.ps1 -Restore  # restore latest backup
#   .\scripts\backup.ps1 -Restore -File "C:\path\to\backup.zip"

param(
    [switch]$Restore,
    [string]$File
)

$INSTALL_DIR = "$env:LOCALAPPDATA\HomerFindr"
$DB_PATH     = "$env:USERPROFILE\.homesearch\homesearch.db"
$BACKUP_DIR  = "$env:USERPROFILE\.homesearch\backups"
$KEEP_COUNT  = 7

function Write-OK($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Step($msg) { Write-Host "  → $msg" -ForegroundColor Cyan }
function Write-Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red }

if (-not $Restore) {
    # ── Create backup ─────────────────────────────────────────────────────────
    New-Item -ItemType Directory -Force -Path $BACKUP_DIR | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $tmpDir = Join-Path $env:TEMP "homerfindr_$stamp"
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

    Write-Step "Creating backup homerfindr_$stamp..."

    $copied = 0
    if (Test-Path $DB_PATH) {
        Copy-Item $DB_PATH "$tmpDir\homesearch.db"
        $copied++
    }
    $vapid = "$env:USERPROFILE\.homesearch\vapid_private.pem"
    if (Test-Path $vapid) {
        Copy-Item $vapid "$tmpDir\vapid_private.pem"
        $copied++
    }
    $envFile = "$INSTALL_DIR\.env"
    if (Test-Path $envFile) {
        Copy-Item $envFile "$tmpDir\.env"
        $copied++
    }

    if ($copied -eq 0) {
        Write-Err "Nothing to back up — HomerFindr data not found at expected paths."
        Remove-Item -Recurse -Force $tmpDir
        exit 1
    }

    $zipPath = Join-Path $BACKUP_DIR "homerfindr_$stamp.zip"
    Compress-Archive -Path "$tmpDir\*" -DestinationPath $zipPath -Force
    Remove-Item -Recurse -Force $tmpDir

    Write-OK "Backup saved: $zipPath"

    # Prune old backups — keep last $KEEP_COUNT
    $old = Get-ChildItem $BACKUP_DIR -Filter "*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -Skip $KEEP_COUNT
    foreach ($f in $old) { Remove-Item $f.FullName -Force }
    if ($old.Count -gt 0) { Write-Host "  (pruned $($old.Count) old backup(s))" -ForegroundColor DarkGray }

} else {
    # ── Restore ───────────────────────────────────────────────────────────────
    if (-not $File) {
        # Use the most recent backup
        $File = Get-ChildItem $BACKUP_DIR -Filter "*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
        if (-not $File) {
            Write-Err "No backups found in $BACKUP_DIR"
            exit 1
        }
        Write-Step "Restoring latest: $File"
    } else {
        Write-Step "Restoring from: $File"
    }

    # Stop service
    Stop-ScheduledTask -TaskName "HomerFindr" -ErrorAction SilentlyContinue

    $tmpDir = Join-Path $env:TEMP "homerfindr_restore"
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
    Expand-Archive -Path $File -DestinationPath $tmpDir -Force

    if (Test-Path "$tmpDir\homesearch.db") {
        New-Item -ItemType Directory -Force -Path (Split-Path $DB_PATH) | Out-Null
        Copy-Item "$tmpDir\homesearch.db" $DB_PATH -Force
        Write-OK "Database restored"
    }
    if (Test-Path "$tmpDir\vapid_private.pem") {
        Copy-Item "$tmpDir\vapid_private.pem" "$env:USERPROFILE\.homesearch\" -Force
        Write-OK "VAPID key restored"
    }
    if (Test-Path "$tmpDir\.env") {
        Copy-Item "$tmpDir\.env" "$INSTALL_DIR\.env" -Force
        Write-OK ".env restored"
    }

    Remove-Item -Recurse -Force $tmpDir

    # Restart service
    Start-ScheduledTask -TaskName "HomerFindr" -ErrorAction SilentlyContinue
    Write-OK "Restore complete → http://127.0.0.1:8000"
}
