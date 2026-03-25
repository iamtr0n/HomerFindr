---
phase: 02-cli-settings-and-configuration
verified: 2026-03-25T00:00:00Z
status: human_needed
score: 11/11 must-haves verified
human_verification:
  - test: "Delete ~/.homerfindr/config.json, run `uv run homesearch` (or `python main.py`), confirm first-run wizard banner appears with city/state/radius/SMTP prompts"
    expected: "Welcome to HomerFindr! banner in a cyan Panel, wizard collects city, state, radius, SMTP choice, then saves config and shows green success Panel"
    why_human: "Questionary prompts require an interactive TTY — cannot drive with grep or import checks"
  - test: "Run app after config exists, confirm first-run wizard does NOT appear"
    expected: "Splash screen followed directly by the main menu; no first-run prompts"
    why_human: "Conditional flow through config_exists() only verifiable live"
  - test: "From main menu select Settings -> Email Settings -> Configure SMTP, walk through provider wizard, verify Gmail App Password hint appears"
    expected: "Provider list shows Gmail/Outlook-Hotmail/Yahoo/Custom; Gmail hint printed; masked password field; test-send offered"
    why_human: "SMTP wizard is interactive; test-send requires live SMTP credentials or a mock server"
  - test: "From Settings -> Search Defaults, edit City and Radius, exit, re-enter Settings, confirm values persisted in displayed Panel summary"
    expected: "Updated values shown in the cyan Panel at top of Search Defaults sub-page"
    why_human: "Persistence check requires reading ~/.homerfindr/config.json via the live UI flow"
  - test: "From Settings -> Email Settings -> Manage Recipients, add an email address (with @), confirm it appears in the Remove list"
    expected: "New recipient visible in the Remove: list; config file updated"
    why_human: "Interactive questionary flow; cannot simulate .ask() return values in a headless check"
  - test: "From main menu select Saved Searches with no saved searches present, verify empty-state message"
    expected: "Yellow text: No saved searches yet. Run a search from the main menu to save one."
    why_human: "Requires a clean database state to trigger the empty-state branch"
  - test: "After saving a search via New Search, open Saved Searches, confirm Rich table with Name/Location/Last Run/Active columns, then test Toggle Active/Inactive, Rename, and Delete (with No confirmation)"
    expected: "Table renders correctly; toggle updates Active checkmark; rename changes name; delete with No cancels; delete with Yes removes row"
    why_human: "Requires live database with a saved search; all actions need TTY interaction"
---

# Phase 02: CLI Settings and Configuration — Verification Report

**Phase Goal:** Build the CLI Settings & Configuration system — persistent config file, SMTP setup wizard, first-run wizard, settings page (Email/Defaults/About), and saved searches browser with full management actions. Wire everything into the main menu.
**Verified:** 2026-03-25
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All 11 must-have truths derived from the three PLAN frontmatter blocks were verified programmatically.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `load_config()` returns a valid dict with defaults, smtp, and version keys even when no config file exists | VERIFIED | config.py lines 40-46: missing-file path returns `copy.deepcopy(DEFAULT_CONFIG)` which has all three top-level keys |
| 2 | `save_config()` creates `~/.homerfindr/config.json` with proper JSON and creates parent directory if missing | VERIFIED | config.py lines 57-60: `CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)` then `json.dumps(config, indent=2)` |
| 3 | SMTP wizard collects provider, server, port, email, password via questionary and returns a dict | VERIFIED | smtp_wizard.py lines 20-80: all five fields collected; return dict at line 73 |
| 4 | SMTP test-send connects via `smtplib.SMTP` with `starttls` and `timeout=10` | VERIFIED | smtp_wizard.py line 91: `smtplib.SMTP(smtp_cfg["server"], smtp_cfg["port"], timeout=10)` with `server.starttls()` on line 92 |
| 5 | First-run wizard triggers only when `~/.homerfindr/config.json` does not exist | VERIFIED | menu.py lines 19-22: `if not config_exists(): run_first_run_wizard()` before `run_menu_loop()` |
| 6 | First-run wizard collects city, state, radius, and optionally runs SMTP setup | VERIFIED | first_run.py lines 23-58: city, state, radius select, smtp_choice; single `save_config(config)` at line 67 |
| 7 | Settings menu shows three categories: Email Settings, Search Defaults, About HomerFindr | VERIFIED | settings.py lines 15-27: `questionary.select` with exact three choices plus Back |
| 8 | Email Settings lets user view/edit SMTP config and manage recipients (add/remove) | VERIFIED | settings.py `_show_email_settings()` (line 30) and `_manage_recipients()` (line 62) both implemented substantively |
| 9 | Search Defaults lets user set default city, state, radius, listing type, price range | VERIFIED | settings.py `_show_search_defaults()` (line 88): all five fields handled with `save_config()` on each update |
| 10 | Saved searches browser shows a Rich table with Name, Location, Last Run, Active columns | VERIFIED | saved_browser.py lines 40-53: `Table` with four columns, correct styles, iterates over search objects |
| 11 | User can Run Now, Toggle Active/Inactive, Rename, and Delete a saved search (Delete confirms with default=False) | VERIFIED | saved_browser.py lines 56-120: all four actions dispatched; `questionary.confirm(..., default=False)` at line 109 |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `homesearch/tui/config.py` | Config load/save foundation | VERIFIED | 61 lines; exports `CONFIG_PATH`, `DEFAULT_CONFIG`, `config_exists`, `load_config`, `save_config`; all substantive |
| `homesearch/tui/smtp_wizard.py` | SMTP wizard with provider presets and test-send | VERIFIED | 122 lines; exports `PROVIDER_PRESETS`, `run_smtp_wizard`, `test_smtp`, `run_smtp_wizard_with_test`; all substantive |
| `homesearch/tui/first_run.py` | First-run setup wizard | VERIFIED | 77 lines; exports `run_first_run_wizard`; single `save_config` call; `KeyboardInterrupt` handled |
| `homesearch/tui/settings.py` | Settings menu with Email, Search Defaults, About | VERIFIED | 186 lines; exports `show_settings_menu`; all three sub-pages implemented; Back as first choice in every menu |
| `homesearch/tui/saved_browser.py` | Saved searches browser with table and action sub-menu | VERIFIED | 121 lines; exports `show_saved_searches_browser`; all seven helper functions present |
| `homesearch/tui/menu.py` | Wired main menu with first-run, settings, saved searches | VERIFIED | 88 lines; three wiring points active; old stubs replaced |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `first_run.py` | `config.py` | `load_config`, `save_config` | WIRED | Line 7: `from homesearch.tui.config import load_config, save_config`; both called in body |
| `first_run.py` | `smtp_wizard.py` | `run_smtp_wizard_with_test` | WIRED | Line 8: `from homesearch.tui.smtp_wizard import run_smtp_wizard_with_test`; called at line 58 |
| `smtp_wizard.py` | `config.py` | `load_config` | WIRED | Line 9: `from homesearch.tui.config import load_config`; called at line 23 when `existing is None` |
| `settings.py` | `smtp_wizard.py` | `run_smtp_wizard_with_test` | WIRED | Line 8: `from homesearch.tui.smtp_wizard import run_smtp_wizard_with_test`; called at line 53 |
| `settings.py` | `config.py` | `load_config`, `save_config` | WIRED | Line 7: `from homesearch.tui.config import load_config, save_config`; called throughout |
| `saved_browser.py` | `homesearch.database` | `init_db`, `get_saved_searches`, `update_search`, `delete_search` | WIRED | Lazy imports inside functions (lines 14, 76, 87, 101, 115); all four DB functions confirmed present in `database.py` |
| `saved_browser.py` | `results.py` | `execute_search_with_spinner`, `display_results` | WIRED | Line 77: lazy import; both functions called in `_run_search_now()` |
| `menu.py` | `first_run.py` | `config_exists()` + `run_first_run_wizard()` in `tui_main()` | WIRED | Lines 19-22: lazy imports + conditional call before `run_menu_loop()` |
| `menu.py` | `settings.py` | `show_settings_menu()` in `_handle_settings()` | WIRED | Lines 81-82: lazy import + direct call; old stub text absent |
| `menu.py` | `saved_browser.py` | `show_saved_searches_browser()` in `_handle_saved_searches()` | WIRED | Lines 75-76: lazy import + direct call; old `execute_search_with_spinner` stub confirmed absent |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CFG-01 | 02-02, 02-03 | Settings page accessible from main menu — view/edit all configuration | SATISFIED | `show_settings_menu()` wired in `_handle_settings()`; three sub-pages (Email, Defaults, About) all implemented |
| CFG-02 | 02-01 | SMTP setup wizard with guided arrow-key flow (server, port, email, password, test send) | SATISFIED | `smtp_wizard.py` implements all five collection steps plus `test_smtp` and retry/save-anyway flow |
| CFG-03 | 02-02 | Email recipients management — add/remove recipients via arrow-key interface | SATISFIED | `_manage_recipients()` in settings.py handles add (with @ validation) and remove via questionary.select |
| CFG-04 | 02-02 | Search defaults configuration — set default location, radius, price range | SATISFIED | `_show_search_defaults()` handles city, state, radius, listing type, and price range with save on each edit |
| CFG-05 | 02-01, 02-03 | First-run experience — guided setup on first launch (location preferences, optional SMTP) | SATISFIED | `first_run.py` + `if not config_exists():` gate in `tui_main()`; collects city, state, radius, optional SMTP |
| CFG-06 | 02-02, 02-03 | Saved searches browser — arrow-key list to view, run, toggle active/inactive, delete | SATISFIED | `saved_browser.py` with Rich table, Run Now, Toggle, Rename, Delete (confirm default=False) all wired |
| CFG-07 | 02-01 | Configuration stored in `~/.homerfindr/config.json` | SATISFIED | `CONFIG_PATH = Path.home() / ".homerfindr" / "config.json"` at config.py line 9 |

All 7 requirements satisfied. No orphaned requirements found.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `menu.py` | 87 | `_handle_web_ui` stub: "Web UI launch will be available in a future update." | Info | Expected — Phase 4 is not yet implemented; this is an intentional future stub, not a Phase 2 concern |

No blockers or warnings found in Phase 2 files.

---

### Human Verification Required

All automated checks pass. The following items require a human with an interactive terminal to confirm end-to-end behavior.

#### 1. First-Run Wizard Trigger

**Test:** Delete `~/.homerfindr/config.json`, then run `uv run homesearch` or `cd /Users/iamtron/Documents/GitHub/HomerFindr && python main.py`
**Expected:** After splash, a cyan Panel titled "First-Time Setup" appears. User enters city, state, selects radius with arrow keys, chooses Skip for SMTP. Green success Panel appears. Running again skips the wizard.
**Why human:** `questionary` prompts require an interactive TTY.

#### 2. Settings — SMTP Wizard Flow

**Test:** From main menu, select Settings -> Email Settings -> Configure SMTP. Choose Gmail.
**Expected:** Gmail App Password hint appears in dim text. Password field is masked. After entering credentials, test email is sent. On test failure, "Retry settings" or "Save anyway" choices appear.
**Why human:** Interactive prompt flow; live SMTP credentials needed for full test-send validation.

#### 3. Settings — Persistent Search Defaults

**Test:** Settings -> Search Defaults -> City, enter a new value. Exit fully. Re-enter Settings -> Search Defaults.
**Expected:** The cyan Panel summary at the top of Search Defaults reflects the updated city.
**Why human:** Persistence round-trip through `~/.homerfindr/config.json` requires live UI navigation.

#### 4. Saved Searches — Empty State

**Test:** Ensure no saved searches in the database (`rm -f ~/.homesearch/homesearch.db`). Select Saved Searches from main menu.
**Expected:** Yellow message: "No saved searches yet. Run a search from the main menu to save one."
**Why human:** Requires controlled database state.

#### 5. Saved Searches — Full Table and Actions

**Test:** Save a search via New Search. Open Saved Searches. Verify table. Test Toggle (check Active column changes), Rename (verify name updates in table on next render), Delete with "No" (cancels), Delete with "Yes" (removes row).
**Expected:** Rich table with Name/Location/Last Run/Active columns. All four actions work correctly.
**Why human:** Requires a saved search in the database plus interactive action selection.

#### 6. Recipients Management

**Test:** Settings -> Email Settings -> Manage Recipients -> Add new recipient. Enter `test@example.com`. Verify it appears as "Remove: test@example.com". Select it to remove.
**Expected:** Recipient added to list and persisted in config; Remove entry appears; removal clears it from list and config.
**Why human:** Interactive questionary flow through two levels of nested menu.

---

### Summary

Phase 02 is fully implemented and all automated checks pass. Every required module exists, is substantive (not a stub), and is wired into the menu system. All 7 CFG requirements are covered. The only items remaining are human-driven end-to-end interaction tests — there are no code gaps, missing wiring, or placeholder implementations to fix.

The single "will be available in a future update" line in `menu.py` belongs to `_handle_web_ui()` and is the correct placeholder for Phase 4 web UI launch — it is not a Phase 2 deficiency.

---

_Verified: 2026-03-25_
_Verifier: Claude (gsd-verifier)_
