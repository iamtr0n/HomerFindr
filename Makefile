# HomerFindr — Build, Deploy & Backup
#
#   make build            Rebuild the React frontend
#   make deploy           Build + sync to running Homebrew install + restart
#   make install          First-time local dev install (pipx)
#   make update           git pull + rebuild + redeploy
#   make backup           Back up database and config to ~/.homesearch/backups/
#   make restore F=<file> Restore from a backup file
#   make release V=x.y.z  Tag release → GitHub Actions builds installers
#   make help             Show this list

# Resolve the live Homebrew libexec path — works regardless of formula version
BREW_LIBEXEC  := $(shell brew --prefix homerfindr 2>/dev/null)/libexec
BREW_VENV     := $(BREW_LIBEXEC)/.venv
PLIST         := $(HOME)/Library/LaunchAgents/com.homerfindr.plist
DB_PATH       := $(HOME)/.homesearch/homesearch.db
BACKUP_DIR    := $(HOME)/.homesearch/backups

.PHONY: build deploy install update backup restore release clean help

# ── Build ──────────────────────────────────────────────────────────────────────
build:
	@echo "→ Building frontend..."
	cd frontend && npm install --silent && npm run build --silent
	@echo "✓ Frontend built → frontend/dist/"

# ── Deploy to the running Homebrew install ─────────────────────────────────────
deploy: build
	@if [ ! -d "$(BREW_LIBEXEC)" ]; then \
	  echo "✗ HomerFindr Homebrew install not found."; \
	  echo "  Install first: brew install --build-from-source homebrew-formula/homerfindr.rb"; \
	  exit 1; \
	fi
	@echo "→ Syncing to $(BREW_LIBEXEC)..."
	rsync -a --delete \
	  --exclude='.git' \
	  --exclude='node_modules' \
	  --exclude='__pycache__' \
	  --exclude='*.egg-info' \
	  --exclude='.venv' \
	  --exclude='.env' \
	  . "$(BREW_LIBEXEC)/"
	@echo "→ Reinstalling Python package..."
	"$(BREW_VENV)/bin/pip" install --quiet -e "$(BREW_LIBEXEC)"
	@echo "→ Restarting service..."
	-launchctl unload "$(PLIST)" 2>/dev/null
	launchctl load "$(PLIST)"
	@echo "✓ Deployed and restarted → http://127.0.0.1:8000"

# ── First-time local dev install ───────────────────────────────────────────────
install: build
	pipx install --editable . --force
	@echo "✓ Installed. Run: homerfindr serve"

# ── Pull latest + redeploy ─────────────────────────────────────────────────────
update:
	@echo "→ Pulling latest..."
	git pull --quiet
	$(MAKE) deploy

# ── Backup ────────────────────────────────────────────────────────────────────
backup:
	@mkdir -p "$(BACKUP_DIR)"
	@STAMP=$$(date +%Y%m%d_%H%M%S); \
	DEST="$(BACKUP_DIR)/homerfindr_$$STAMP"; \
	mkdir -p "$$DEST"; \
	[ -f "$(DB_PATH)" ] && cp "$(DB_PATH)" "$$DEST/homesearch.db" || true; \
	[ -f "$(HOME)/.homesearch/vapid_private.pem" ] && cp "$(HOME)/.homesearch/vapid_private.pem" "$$DEST/" || true; \
	[ -f "$(BREW_LIBEXEC)/.env" ] && cp "$(BREW_LIBEXEC)/.env" "$$DEST/.env" || true; \
	[ -f ".env" ] && cp ".env" "$$DEST/.env" 2>/dev/null || true; \
	tar -czf "$(BACKUP_DIR)/homerfindr_$$STAMP.tar.gz" -C "$(BACKUP_DIR)" "homerfindr_$$STAMP"; \
	rm -rf "$$DEST"; \
	echo "✓ Backup saved: $(BACKUP_DIR)/homerfindr_$$STAMP.tar.gz"; \
	ls -t "$(BACKUP_DIR)"/*.tar.gz 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null; \
	echo "  (keeping last 7 backups)"

# ── Restore ───────────────────────────────────────────────────────────────────
restore:
	@test -n "$(F)" || (echo "Usage: make restore F=~/.homesearch/backups/homerfindr_YYYYMMDD_HHMMSS.tar.gz" && exit 1)
	@echo "→ Restoring from $(F)..."
	@-launchctl unload "$(PLIST)" 2>/dev/null
	@TMPDIR=$$(mktemp -d); \
	tar -xzf "$(F)" -C "$$TMPDIR"; \
	INNER=$$(ls "$$TMPDIR"); \
	[ -f "$$TMPDIR/$$INNER/homesearch.db" ] && cp "$$TMPDIR/$$INNER/homesearch.db" "$(DB_PATH)" && echo "  ✓ Database restored" || true; \
	[ -f "$$TMPDIR/$$INNER/vapid_private.pem" ] && cp "$$TMPDIR/$$INNER/vapid_private.pem" "$(HOME)/.homesearch/" && echo "  ✓ VAPID key restored" || true; \
	[ -f "$$TMPDIR/$$INNER/.env" ] && cp "$$TMPDIR/$$INNER/.env" "$(BREW_LIBEXEC)/.env" && echo "  ✓ .env restored" || true; \
	rm -rf "$$TMPDIR"
	-launchctl load "$(PLIST)" 2>/dev/null
	@echo "✓ Restore complete → http://127.0.0.1:8000"

# ── Schedule daily automatic backups (macOS) ──────────────────────────────────
BACKUP_PLIST_SRC := $(CURDIR)/scripts/com.homerfindr.backup.plist
BACKUP_PLIST_DST := $(HOME)/Library/LaunchAgents/com.homerfindr.backup.plist

setup-backup:
	sed 's|INSTALL_DIR_PLACEHOLDER|$(CURDIR)|g' "$(BACKUP_PLIST_SRC)" > "$(BACKUP_PLIST_DST)"
	-launchctl unload "$(BACKUP_PLIST_DST)" 2>/dev/null
	launchctl load "$(BACKUP_PLIST_DST)"
	@echo "✓ Daily backup scheduled at 3 AM → $(BACKUP_DIR)"
	@echo "  Logs: /tmp/homerfindr-backup.log"

list-backups:
	@ls -lht "$(BACKUP_DIR)"/*.tar.gz 2>/dev/null || echo "No backups found in $(BACKUP_DIR)"

# ── Release: bump version, tag, push → GitHub Actions builds installers ────────
release:
	@test -n "$(V)" || (echo "Usage: make release V=1.3.0" && exit 1)
	@echo "→ Releasing v$(V)..."
	sed -i '' 's/^version = ".*"/version = "$(V)"/' pyproject.toml
	git add pyproject.toml
	git commit -m "chore: bump version to $(V)"
	git tag -a "v$(V)" -m "Release v$(V)"
	git push origin main "v$(V)"
	@echo "✓ Tag pushed → GitHub Actions will build Mac + Windows installers"
	@echo "  https://github.com/iamtr0n/HomerFindr/actions"

# ── Clean build artifacts ─────────────────────────────────────────────────────
clean:
	rm -rf frontend/dist frontend/node_modules __pycache__ homesearch.egg-info

# ── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  HomerFindr Build Commands"
	@echo "  ─────────────────────────────────────────────────────"
	@echo "  make build              Rebuild the React frontend"
	@echo "  make deploy             Build + sync to Homebrew + restart"
	@echo "  make install            First-time local dev install (pipx)"
	@echo "  make update             git pull + rebuild + redeploy"
	@echo "  make backup             Back up DB + config → ~/.homesearch/backups/"
	@echo "  make restore F=<file>   Restore from a backup .tar.gz"
	@echo "  make setup-backup       Schedule daily auto-backup at 3 AM (macOS)"
	@echo "  make list-backups       Show all backups on disk"
	@echo "  make release V=x.y.z    Tag release, trigger GitHub Actions"
	@echo "  make clean              Remove build artifacts"
	@echo ""
