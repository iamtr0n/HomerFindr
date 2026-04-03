@echo off
title HomerFindr Installer
color 0A
cls

echo.
echo   ██╗  ██╗ ██████╗ ███╗   ███╗███████╗██████╗
echo   ██║  ██║██╔═══██╗████╗ ████║██╔════╝██╔══██╗
echo   ███████║██║   ██║██╔████╔██║█████╗  ██████╔╝
echo   ██╔══██║██║   ██║██║╚██╔╝██║██╔══╝  ██╔══██╗
echo   ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗██║  ██║
echo   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
echo.
echo   Universal home search -- all platforms, one place.
echo   ---------------------------------------------------
echo.
echo   This will install HomerFindr on your computer.
echo   It may take a few minutes on first run.
echo.

:: Check that PowerShell is available (it always is on Windows 7+)
where powershell >nul 2>&1
if errorlevel 1 (
  echo   ERROR: PowerShell not found. Please install it from:
  echo   https://aka.ms/powershell
  echo.
  pause
  exit /b 1
)

echo   Starting installer...
echo.

:: -ExecutionPolicy Bypass: allows the script to run without changing system policy
:: -NoProfile: faster startup, avoids profile conflicts
:: irm downloads the script; iex runs it
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { irm 'https://raw.githubusercontent.com/iamtr0n/HomerFindr/main/install.ps1' | iex } catch { Write-Host ''; Write-Host ('  ERROR: ' + $_.Exception.Message) -ForegroundColor Red; Write-Host ''; Write-Host '  Check your internet connection and try again.' -ForegroundColor Yellow; pause }"

echo.
echo   Press any key to close this window.
pause >nul
