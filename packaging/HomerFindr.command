#!/bin/bash
# HomerFindr.command — Double-click to launch HomerFindr CLI in Terminal.
# Make executable: chmod +x HomerFindr.command

# Ensure pipx bin directory is in PATH (handles fresh Terminal sessions)
export PATH="$HOME/.local/bin:$PATH"

# Source shell profile for any additional PATH entries
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" 2>/dev/null
[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc" 2>/dev/null

if command -v homerfindr &>/dev/null; then
    homerfindr
else
    echo ""
    echo "HomerFindr is not installed."
    echo ""
    echo "Install with:"
    echo "  pipx install /path/to/HomerFindr"
    echo ""
    echo "Then run:"
    echo "  pipx ensurepath"
    echo ""
    echo "Press Enter to close."
    read
fi
