---
phase: 02-cli-settings-and-configuration
plan: 01
subsystem: tui-config
tags: [config, smtp, first-run, wizard, tui]
dependency_graph:
  requires: []
  provides: [homesearch.tui.config, homesearch.tui.smtp_wizard, homesearch.tui.first_run]
  affects: [homesearch.tui.menu]
tech_stack:
  added: []
  patterns: [deep-copy-merge-config, smtp-starttls, questionary-wizard]
key_files:
  created:
    - homesearch/tui/config.py
    - homesearch/tui/smtp_wizard.py
    - homesearch/tui/first_run.py
  modified: []
decisions:
  - "Use deep-copy merge over DEFAULT_CONFIG per top-level key so future config keys auto-populate without losing existing values"
  - "test_smtp uses smtplib.SMTP context manager with starttls and timeout=10; retry-or-save-anyway pattern on test failure"
  - "first_run wraps entire body in try/except KeyboardInterrupt to prevent partial saves on Ctrl+C"
metrics:
  duration: 5m
  completed: 2026-03-25
  tasks_completed: 2
  files_created: 3
---

# Phase 2 Plan 1: Config Foundation, SMTP Wizard, and First-Run Wizard Summary

**One-liner:** JSON config load/save with deep-copy merge, SMTP wizard with Gmail/Outlook/Yahoo/Custom presets and test-send, and first-run wizard that collects location defaults and optional SMTP, saving config atomically at end.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create config.py and smtp_wizard.py | 0783b5f | homesearch/tui/config.py, homesearch/tui/smtp_wizard.py |
| 2 | Create first_run.py wizard | 6e9f2c5 | homesearch/tui/first_run.py |

## What Was Built

### config.py
- `CONFIG_PATH = Path.home() / ".homerfindr" / "config.json"`
- `DEFAULT_CONFIG` with `defaults`, `smtp`, and `version: "1.0"` top-level keys
- `config_exists() -> bool`
- `load_config() -> dict` — deep-copy merge strategy; prints dim message on corrupt file
- `save_config(config: dict) -> None` — creates parent directory if missing

### smtp_wizard.py
- `PROVIDER_PRESETS` for Gmail, Outlook/Hotmail, Yahoo, Custom
- `run_smtp_wizard(existing)` — provider select, server/port/email/password collection, masked password via questionary.password(), Gmail App Password hint
- `test_smtp(smtp_cfg)` — smtplib.SMTP with starttls, sends to self, Rich Panel on success
- `run_smtp_wizard_with_test(existing)` — orchestrates wizard + test with "Retry settings" / "Save anyway (skip test)" on failure

### first_run.py
- `run_first_run_wizard()` — welcome banner, city/state/radius/smtp steps, single save_config() call at end
- Full KeyboardInterrupt guard at top level (no partial saves)
- Radius via questionary.select with Choice objects (5/10/25/50 miles)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all three modules are fully functional. No hardcoded empty values flow to UI rendering. Wiring into menu.py is intentionally deferred to Plan 03 per plan objective.

## Self-Check: PASSED

- homesearch/tui/config.py: FOUND
- homesearch/tui/smtp_wizard.py: FOUND
- homesearch/tui/first_run.py: FOUND
- Commit 0783b5f: FOUND
- Commit 6e9f2c5: FOUND
- All three modules import cleanly: VERIFIED
