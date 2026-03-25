---
phase: 01-interactive-cli-core
plan: "04"
subsystem: tui
tags: [cli, tui, search, results, threading, rich, questionary]
dependency_graph:
  requires: [01-02, 01-03]
  provides: [results-display, search-execution-spinner, save-search-flow]
  affects: [homesearch/tui/menu.py]
tech_stack:
  added: []
  patterns:
    - threading.Thread(daemon=True) for non-blocking search execution
    - Rich Live context exited fully before questionary prompts (terminal ownership sequencing)
    - Provider name cycling in spinner text for animated feedback
key_files:
  created:
    - homesearch/tui/results.py
  modified:
    - homesearch/tui/menu.py
decisions:
  - Rich Live must exit before questionary to prevent terminal ownership conflicts (reinforces D from 01-02)
  - display_results capped at 50 results shown in table with dim note for overflow
  - url_map keyed on label string (index + truncated address) for O(1) URL lookup after selection
metrics:
  duration_minutes: 2
  completed_date: "2026-03-25T21:59:14Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 01 Plan 04: Search Spinner, Results Display, and Save Flow Summary

**One-liner:** Threading-based search spinner cycling provider names with Rich Live, colorful results table, browser URL opener, and save-to-SQLite flow via questionary prompts.

## What Was Built

The final piece of the Phase 01 interactive CLI: a complete end-to-end search execution flow wired into the main menu.

### homesearch/tui/results.py (created, 174 lines)

`execute_search_with_spinner(criteria)` — runs `run_search()` on a `daemon=True` background thread. A `threading.Event` signals completion. While waiting, `Rich Live` animates a braille spinner that cycles through provider names (e.g., "Searching HomeHarvest...", "Searching Redfin...") at 10 fps. The `Live` context exits fully before any console output or questionary prompt fires.

`display_results(results, criteria)` — renders a Rich `Table` with colored columns: Address (white), Price (green), Bed/Ba (cyan), SqFt (yellow), Year (dim), Source (dim). A `Panel` header shows the total listing count and provider count. Up to 50 listings are displayed; overflow is noted with a dim message. After the table, `questionary.select` lets the user arrow-key through listings with URLs to open in the system browser via `webbrowser.open()`. After URL selection, `_offer_save_search()` prompts "Save this search?" and if Yes, prompts for a name and persists a `SavedSearch` to SQLite via `db.save_search()`.

### homesearch/tui/menu.py (modified)

`_handle_new_search()` — replaced placeholder stub with full flow: `run_search_wizard()` -> `execute_search_with_spinner()` -> `display_results()`.

`_handle_saved_searches()` — replaced read-only list with run-capable flow: select a saved search -> `execute_search_with_spinner(selected.criteria)` -> `display_results()`. All placeholder strings ("coming in next plan", "coming in Plan 04") removed.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Build search execution spinner and results display | ad1b528 | homesearch/tui/results.py (created) |
| 2 | Wire search execution and saved searches into menu | 5e6e041 | homesearch/tui/menu.py (modified) |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All search-path stubs have been replaced with live functionality. Settings and Web UI menu handlers remain as intentional Phase 2/4 stubs outside the scope of this plan.

## Self-Check: PASSED

- homesearch/tui/results.py: FOUND (174 lines)
- homesearch/tui/menu.py: FOUND (modified, no placeholders)
- Commit ad1b528: FOUND
- Commit 5e6e041: FOUND
- Import check: `from homesearch.tui.results import execute_search_with_spinner, display_results` exits 0
- grep "execute_search_with_spinner" menu.py: FOUND
- grep -c "coming in" menu.py: 0
