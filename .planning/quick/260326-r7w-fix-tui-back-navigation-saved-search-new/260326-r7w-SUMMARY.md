# Quick Task 260326-r7w: Fix TUI Back Navigation

**Date:** 2026-03-26
**Status:** Complete

## Changes Made

### 1. results.py — Clearer "Back to main menu" label
- `"✕  Exit"` → `"← Back to main menu"` so users know exactly where they're going

### 2. menu.py — `_handle_new_search()` now loops on "New search"
- Was: ignored `display_results()` return value, always returned to menu
- Now: loops the wizard again if user picks "↩ New search" from results; returns to menu only when they pick "← Back to main menu"

### 3. saved_browser.py — `_run_search_now()` honors "New search"
- Was: ignored return value from `display_results()`, silently returned to saved browser
- Now: if user picks "↩ New search" from results, calls `_handle_new_search()` to launch the full wizard loop

### 4. zip_browser.py — Discoverable Esc hint in prompts
- Both county and ZIP checkbox prompts now read `(Space=toggle, Enter=confirm, Esc=back)` so the back gesture is discoverable without adding an awkward checkbox item
