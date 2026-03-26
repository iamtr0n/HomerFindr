#!/bin/bash
# homerfindr_launcher.sh — Script for Platypus to wrap as macOS .app
# Platypus config: Interface: None (this script opens Terminal itself)
#
# Build .app with Platypus CLI:
#   /usr/local/bin/platypus \
#     --name "HomerFindr" \
#     --interface-type None \
#     --author "HomerFindr" \
#     --bundle-identifier "com.homerfindr.app" \
#     --overwrite \
#     packaging/homerfindr_launcher.sh \
#     packaging/HomerFindr.app
#
# Then copy to Applications:
#   cp -r packaging/HomerFindr.app /Applications/

# Ensure pipx bin is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Open a new Terminal window running homerfindr
osascript -e 'tell application "Terminal" to do script "export PATH=\"$HOME/.local/bin:$PATH\"; homerfindr"'
