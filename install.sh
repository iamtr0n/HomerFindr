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

# ─────────────────────────────────────────────
# SMS ALERT SETUP (optional, free via Zapier)
# ─────────────────────────────────────────────
echo ""
echo "  ─────────────────────────────────────────"
echo "  📱  Want SMS alerts when new homes hit?"
echo "     Free Zapier account — takes 3 minutes."
echo "  ─────────────────────────────────────────"
echo ""
read -p "  Set up SMS alerts now? (y/n): " SETUP_SMS
echo ""

if [[ "$SETUP_SMS" =~ ^[Yy]$ ]]; then

  read -p "  Your phone number (e.g. +12125551234): " PHONE_NUMBER
  echo ""

  # Generate a unique webhook URL placeholder they'll fill in after Zapier
  echo -e "  ${BLUE}Step 1 — Create a free Zapier account${NC}"
  echo "  ➜ Go to: https://zapier.com/sign-up  (free, no credit card)"
  echo ""
  echo -e "  ${BLUE}Step 2 — Create a new Zap${NC}"
  echo "  ➜ Click \"Create\" → \"New Zap\""
  echo ""
  echo -e "  ${BLUE}Step 3 — Paste this into Zapier's AI prompt box${NC}"
  echo ""
  echo "  ┌─────────────────────────────────────────────────────────────────┐"
  echo "  │  Copy everything between the lines:                            │"
  echo "  ├─────────────────────────────────────────────────────────────────┤"
  cat << ZAPIER_PROMPT

  Create a Zap with these exact settings:

  TRIGGER:
  - App: Webhooks by Zapier
  - Event: Catch Hook
  - (Copy the webhook URL it generates — you will need it in a moment)

  ACTION:
  - App: SMS by Zapier
  - Event: Send SMS
  - To: ${PHONE_NUMBER}
  - Message:
    🏠 HomerFindr Alert
    {{new_count}} new home(s) for "{{search_name}}"

    📍 {{listings__1__address}}
    💰 \${{listings__1__price}}
    🛏 {{listings__1__beds}} bed / {{listings__1__baths}} bath
    📐 {{listings__1__sqft}} sqft
    🔗 {{listings__1__url}}

    Open HomerFindr: http://127.0.0.1:8000

  Turn the Zap ON when done.

ZAPIER_PROMPT
  echo "  └─────────────────────────────────────────────────────────────────┘"
  echo ""
  echo -e "  ${BLUE}Step 4 — Paste your webhook URL here${NC}"
  echo "  (After Zapier generates your Catch Hook URL, paste it below)"
  echo ""
  read -p "  Zapier webhook URL: " WEBHOOK_URL
  echo ""

  if [[ -n "$WEBHOOK_URL" ]]; then
    # Write to .env
    if grep -q "ZAPIER_WEBHOOK_URL" "$INSTALL_DIR/.env" 2>/dev/null; then
      sed -i '' "s|ZAPIER_WEBHOOK_URL=.*|ZAPIER_WEBHOOK_URL=$WEBHOOK_URL|" "$INSTALL_DIR/.env"
    else
      echo "" >> "$INSTALL_DIR/.env"
      echo "# Zapier webhook for SMS alerts" >> "$INSTALL_DIR/.env"
      echo "ZAPIER_WEBHOOK_URL=$WEBHOOK_URL" >> "$INSTALL_DIR/.env"
    fi

    # Restart server to pick up new .env
    launchctl unload "$PLIST" 2>/dev/null || true
    sleep 1
    launchctl load "$PLIST"

    # Send a test notification
    sleep 3
    curl -s -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "{\"search_name\":\"Test Alert\",\"new_count\":1,\"listings\":[{\"address\":\"123 Main St, Anytown USA\",\"price\":450000,\"beds\":3,\"baths\":2,\"sqft\":1800,\"url\":\"http://127.0.0.1:8000\"}]}" \
      > /dev/null

    echo -e "  ${GREEN}✓ Webhook saved and test alert sent!${NC}"
    echo "  Check your phone — you should receive a test SMS within 30 seconds."
    echo ""
    echo "  You're all set. Every saved search will now text you when new homes hit."
  else
    echo "  Skipped — you can add it later by editing: $INSTALL_DIR/.env"
    echo "  Add this line:  ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/..."
  fi

else
  echo "  Skipped. You can set up SMS alerts anytime by editing:"
  echo "  $INSTALL_DIR/.env  →  add:  ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/..."
  echo ""
fi

echo -e "  ${GREEN}HomerFindr setup complete. Happy house hunting! 🏠${NC}"
echo ""
