#!/bin/bash
# HomerFindr — macOS Installer
#
# HOW TO USE:
#   Double-click this file in Finder.
#
# If macOS says "cannot be opened because the developer cannot be verified":
#   Right-click the file → Open → Open
#   (Only needed once — macOS remembers your choice)
#
# ─────────────────────────────────────────────────────────────────────────────

# Keep the Terminal window open if something goes wrong
trap 'echo ""; echo "  Press Enter to close."; read' EXIT

clear
echo ""
echo "  ██╗  ██╗ ██████╗ ███╗   ███╗███████╗██████╗ "
echo "  ██║  ██║██╔═══██╗████╗ ████║██╔════╝██╔══██╗"
echo "  ███████║██║   ██║██╔████╔██║█████╗  ██████╔╝"
echo "  ██╔══██║██║   ██║██║╚██╔╝██║██╔══╝  ██╔══██╗"
echo "  ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗██║  ██║"
echo "  ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝"
echo "              ███████╗██╗███╗   ██╗██████╗ ██████╗ "
echo "              ██╔════╝██║████╗  ██║██╔══██╗██╔══██╗"
echo "              █████╗  ██║██╔██╗ ██║██║  ██║██████╔╝"
echo "              ██╔══╝  ██║██║╚██╗██║██║  ██║██╔══██╗"
echo "              ██║     ██║██║ ╚████║██████╔╝██║  ██║"
echo "              ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝"
echo ""
echo "  ─────────────────────────────────────────────────"
echo "  Universal home search — all platforms, one place."
echo "  ─────────────────────────────────────────────────"
echo ""

# Check for curl (should always exist on macOS)
if ! command -v curl &>/dev/null; then
  echo "  ✗ curl is required but not found. Please install Xcode Command Line Tools:"
  echo "    xcode-select --install"
  exit 1
fi

echo "  Downloading installer..."
echo ""

# Download and run the installer from GitHub
curl -fsSL "https://raw.githubusercontent.com/iamtr0n/HomerFindr/main/install.sh" | bash
