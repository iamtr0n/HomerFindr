#!/bin/bash
# HomerFindr — one-command installer
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/HomerFindr/main/install.sh | bash

set -e

REPO="https://github.com/iamtr0n/HomerFindr.git"
INSTALL_DIR="$HOME/HomerFindr"
PLIST="$HOME/Library/LaunchAgents/com.homerfindr.plist"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "  🏠  HomerFindr Installer"
echo "  ─────────────────────────────"
echo ""

# 1. Check Python 3.11+
if ! command -v python3 &>/dev/null; then
  echo "Python 3.11+ is required. Install from https://www.python.org/downloads/" && exit 1
fi
PY_VER=$(python3 -c 'import sys; print(sys.version_info >= (3,11))')
if [ "$PY_VER" != "True" ]; then
  echo "Python 3.11+ required (you have $(python3 --version)). Install from https://www.python.org/downloads/" && exit 1
fi

# 2. Check Node.js
if ! command -v node &>/dev/null; then
  echo "Node.js is required for the web dashboard. Install from https://nodejs.org" && exit 1
fi

# 3. Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "Updating existing install..."
  git -C "$INSTALL_DIR" pull --quiet
else
  echo "Downloading HomerFindr..."
  git clone --quiet "$REPO" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# 4. Python venv + install
echo "Installing Python dependencies..."
python3 -m venv .venv --quiet
.venv/bin/pip install -e . --quiet

# 5. Build frontend
echo "Building web dashboard..."
cd frontend
npm install --silent
npm run build --silent
cd ..

# 6. Create .env if missing
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "  ⚡  Optional: edit $INSTALL_DIR/.env to add your Zapier webhook for SMS alerts"
fi

# 7. Install launchd service (macOS auto-start)
HOMESEARCH_BIN="$INSTALL_DIR/.venv/bin/homesearch"

cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.homerfindr</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HOMESEARCH_BIN</string>
        <string>serve</string>
    </array>
    <key>WorkingDirectory</key><string>$INSTALL_DIR</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/tmp/homerfindr.log</string>
    <key>StandardErrorPath</key><string>/tmp/homerfindr.err</string>
</dict>
</plist>
EOF
chmod 644 "$PLIST"

# Unload old instance if running, then load fresh
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

# 8. Wait for server
echo "Starting server..."
for i in {1..10}; do
  if curl -s http://127.0.0.1:8000/api/searches &>/dev/null; then break; fi
  sleep 1
done

echo ""
echo -e "  ${GREEN}✓ HomerFindr is running!${NC}"
echo ""
echo -e "  ${BLUE}➜ Open in browser:${NC}  http://127.0.0.1:8000"
echo -e "  ${BLUE}➜ CLI search:${NC}       homesearch search"
echo -e "  ${BLUE}➜ View logs:${NC}        tail -f /tmp/homerfindr.log"
echo -e "  ${BLUE}➜ Stop:${NC}             launchctl unload ~/Library/LaunchAgents/com.homerfindr.plist"
echo ""
echo "  HomerFindr will auto-start every time you log in."
echo ""

# Open browser automatically on Mac
if command -v open &>/dev/null; then
  open http://127.0.0.1:8000
fi
