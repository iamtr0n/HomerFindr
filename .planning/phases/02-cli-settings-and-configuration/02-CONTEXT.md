# Phase 2: CLI Settings and Configuration - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the settings system, SMTP wizard, first-run experience, and saved searches browser. Users can configure everything (email, defaults, saved searches) without leaving the CLI, using the same arrow-key navigation established in Phase 1. Config persists to ~/.homerfindr/config.json.

</domain>

<decisions>
## Implementation Decisions

### SMTP Setup Wizard
- **D-01:** Pre-built provider shortcuts: Gmail, Outlook/Hotmail, Yahoo, Custom — selecting a provider auto-fills server and port
- **D-02:** Fields: server (pre-filled or text), port (pre-filled or text), email (text), password (password — masked input)
- **D-03:** Test send on completion: sends a test email to the configured address, shows Rich success/failure panel
- **D-04:** On test failure: offer "Retry settings" or "Save anyway (skip test)"
- **D-05:** Email recipients management: arrow-key list of current recipients + "Add new" and "Remove" options

### First-Run Experience
- **D-06:** Triggers when ~/.homerfindr/config.json does not exist
- **D-07:** Friendly welcome banner: "Welcome to HomerFindr! Let's get you set up." with house emoji
- **D-08:** Steps: 1) Default city/state (text input), 2) Default radius (arrow select: 5/10/25/50 miles), 3) SMTP setup (arrow: "Set up now" / "Skip for later")
- **D-09:** Creates ~/.homerfindr/config.json on completion with defaults populated
- **D-10:** If SMTP skipped, config still created with empty email section — user can configure later from Settings

### Saved Searches Browser
- **D-11:** Rich table display: Name, Location, Last Run date, Active status (✓/✗) — arrow keys to select row
- **D-12:** On selecting a search: sub-menu with options: "Run Now", "Toggle Active/Inactive", "Rename", "Delete"
- **D-13:** Delete requires confirmation: "Delete 'My Dallas Search'? This cannot be undone." (Yes/No)
- **D-14:** "Run Now" executes the search using Phase 1's execute_search_with_spinner + display_results flow
- **D-15:** Empty state: "No saved searches yet. Run a search from the main menu to save one."

### Settings Page
- **D-16:** Category menu accessible from main menu ⚙️ Settings: "Email Settings", "Search Defaults", "About HomerFindr"
- **D-17:** Email Settings sub-page: view/edit SMTP config, manage recipients (reuses SMTP wizard components)
- **D-18:** Search Defaults sub-page: set default city, radius, property type, price range — all arrow-selectable
- **D-19:** About page: version, ASCII house logo (small), links to docs/repo
- **D-20:** Back navigation: "← Back" option at top of every sub-menu to return to parent

### Config File
- **D-21:** Location: ~/.homerfindr/config.json (created on first run or first settings save)
- **D-22:** Structure: { "defaults": { "city": "", "state": "", "radius": 25, ... }, "smtp": { "provider": "", "server": "", "port": 587, "email": "", "password": "", "recipients": [] }, "version": "1.0" }
- **D-23:** Config module: new homesearch/tui/config.py with load_config() and save_config() functions
- **D-24:** Password stored as plaintext in config (acceptable for personal local tool — not a SaaS)

### Claude's Discretion
- Exact welcome banner ASCII art size (keep small — not the full splash)
- Order of first-run steps if user wants to rearrange
- Config file migration strategy if schema changes later
- Error handling for corrupt config files

</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above and in:

### Project context
- `.planning/PROJECT.md` — Core value, constraints, target users
- `.planning/REQUIREMENTS.md` — CFG-01 through CFG-07 acceptance criteria

### Prior phase
- `.planning/phases/01-interactive-cli-core/01-CONTEXT.md` — Phase 1 decisions (color theme, navigation patterns, questionary usage)

### Research
- `.planning/research/STACK.md` — questionary library details
- `.planning/research/FEATURES.md` — CLI settings feature expectations

### Existing code
- `homesearch/tui/menu.py` — Main menu with Settings and Saved Searches stubs to wire
- `homesearch/tui/styles.py` — Shared color theme constants
- `homesearch/tui/results.py` — execute_search_with_spinner and display_results to reuse for "Run Now"
- `homesearch/config.py` — Existing pydantic Settings (env-based) — new config.json is separate
- `homesearch/database.py` — SavedSearchDB with get_saved_searches, delete_search, update_search

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `homesearch/tui/menu.py`: `_handle_settings()` and `_handle_saved_searches()` are stub functions ready to wire
- `homesearch/tui/results.py`: `execute_search_with_spinner()` and `display_results()` for "Run Now" on saved searches
- `homesearch/tui/styles.py`: THEME colors (PRIMARY, SECONDARY, ACCENT, etc.) for consistent styling
- `homesearch/database.py`: Full SavedSearch CRUD — get_saved_searches(), save_search(), delete_search(), update_search()
- `homesearch/models.py`: SavedSearch model with name, criteria_json, is_active, last_run_at
- `homesearch/services/report_service.py`: send_email_report() — can reuse SMTP connection logic for test send

### Established Patterns
- questionary.select() for arrow-key menus (Phase 1 pattern)
- Rich console for styled output, Rich Table for data display
- Rich Live exits before questionary fires (sequencing rule from Phase 1)
- All config currently via .env + pydantic Settings — new JSON config is a parallel system for TUI preferences

### Integration Points
- `homesearch/tui/menu.py` _handle_settings() → new settings page
- `homesearch/tui/menu.py` _handle_saved_searches() → new saved searches browser
- `homesearch/tui/menu.py` tui_main() → first-run check before menu loop
- ~/.homerfindr/config.json → new file, read by wizard for defaults, read by report service for SMTP

</code_context>

<specifics>
## Specific Ideas

- SMTP provider shortcuts (Gmail/Outlook/Yahoo) are a key UX win — most users use one of these
- First-run should feel welcoming, not like a setup chore — keep it to 3 steps max
- "← Back" navigation in sub-menus is critical — users should never feel trapped
- Reuse Phase 1 patterns exactly: same colors, same questionary style, same Rich output

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-cli-settings-and-configuration*
*Context gathered: 2026-03-25*
