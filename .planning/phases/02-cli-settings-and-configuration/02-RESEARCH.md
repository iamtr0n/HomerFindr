# Phase 2: CLI Settings and Configuration - Research

**Researched:** 2026-03-25
**Domain:** Python TUI (questionary + Rich), JSON config management, SMTP wizard
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**SMTP Setup Wizard**
- D-01: Pre-built provider shortcuts: Gmail, Outlook/Hotmail, Yahoo, Custom — selecting a provider auto-fills server and port
- D-02: Fields: server (pre-filled or text), port (pre-filled or text), email (text), password (password — masked input)
- D-03: Test send on completion: sends a test email to the configured address, shows Rich success/failure panel
- D-04: On test failure: offer "Retry settings" or "Save anyway (skip test)"
- D-05: Email recipients management: arrow-key list of current recipients + "Add new" and "Remove" options

**First-Run Experience**
- D-06: Triggers when ~/.homerfindr/config.json does not exist
- D-07: Friendly welcome banner: "Welcome to HomerFindr! Let's get you set up." with house emoji
- D-08: Steps: 1) Default city/state (text input), 2) Default radius (arrow select: 5/10/25/50 miles), 3) SMTP setup (arrow: "Set up now" / "Skip for later")
- D-09: Creates ~/.homerfindr/config.json on completion with defaults populated
- D-10: If SMTP skipped, config still created with empty email section — user can configure later from Settings

**Saved Searches Browser**
- D-11: Rich table display: Name, Location, Last Run date, Active status (checkmark/X) — arrow keys to select row
- D-12: On selecting a search: sub-menu with options: "Run Now", "Toggle Active/Inactive", "Rename", "Delete"
- D-13: Delete requires confirmation: "Delete 'My Dallas Search'? This cannot be undone." (Yes/No)
- D-14: "Run Now" executes the search using Phase 1's execute_search_with_spinner + display_results flow
- D-15: Empty state: "No saved searches yet. Run a search from the main menu to save one."

**Settings Page**
- D-16: Category menu accessible from main menu Settings: "Email Settings", "Search Defaults", "About HomerFindr"
- D-17: Email Settings sub-page: view/edit SMTP config, manage recipients (reuses SMTP wizard components)
- D-18: Search Defaults sub-page: set default city, radius, property type, price range — all arrow-selectable
- D-19: About page: version, ASCII house logo (small), links to docs/repo
- D-20: Back navigation: "Back" option at top of every sub-menu to return to parent

**Config File**
- D-21: Location: ~/.homerfindr/config.json (created on first run or first settings save)
- D-22: Structure: { "defaults": { "city": "", "state": "", "radius": 25, ... }, "smtp": { "provider": "", "server": "", "port": 587, "email": "", "password": "", "recipients": [] }, "version": "1.0" }
- D-23: Config module: new homesearch/tui/config.py with load_config() and save_config() functions
- D-24: Password stored as plaintext in config (acceptable for personal local tool — not a SaaS)

### Claude's Discretion
- Exact welcome banner ASCII art size (keep small — not the full splash)
- Order of first-run steps if user wants to rearrange
- Config file migration strategy if schema changes later
- Error handling for corrupt config files

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | Settings page accessible from main menu — view/edit all configuration | menu.py _handle_settings() stub ready; questionary.select() sub-menu pattern established |
| CFG-02 | SMTP setup wizard with guided arrow-key flow (server, port, email, password, test send) | questionary.password() confirmed; smtplib.SMTP starttls pattern verified; SMTP_SSL available |
| CFG-03 | Email recipients management — add/remove recipients via arrow-key interface | questionary.select() + questionary.text() combination; list mutation + save_config() |
| CFG-04 | Search defaults configuration — set default location, radius, price range | questionary.select() with Choice; config["defaults"] dict; pre-populate wizard from config |
| CFG-05 | First-run experience — guided setup on first launch (location preferences, optional SMTP) | Path(~/.homerfindr/config.json).exists() trigger; questionary.text() + select() sequence |
| CFG-06 | Saved searches browser — arrow-key list to view, run, toggle active/inactive, delete | database.py get_saved_searches() + update_search() + delete_search() all verified; Rich Table display |
| CFG-07 | Configuration stored in user-friendly location (~/.homerfindr/config.json) | json.dumps/loads confirmed; Path.home() / ".homerfindr" / "config.json"; mkdir parents=True |
</phase_requirements>

---

## Summary

Phase 2 adds the configuration layer — first-run wizard, settings menu, SMTP wizard, and a full saved searches browser — all wired into the existing questionary + Rich TUI established in Phase 1. The technical stack is already in the codebase: questionary 2.1.1 (verified), Rich 13.7+, and Python's stdlib `smtplib` and `json`. No new dependencies are required.

The primary integration points are two stubs in `homesearch/tui/menu.py`: `_handle_settings()` and `_handle_saved_searches()`. The first-run check slots in before the `run_menu_loop()` call in `tui_main()`. A new `homesearch/tui/config.py` module provides `load_config()` / `save_config()` functions that everything else depends on. The config lives at `~/.homerfindr/config.json`, parallel to (and separate from) the existing `.env` + pydantic Settings system.

The SMTP wizard uses `questionary.password()` for masked input (verified in 2.1.1), `smtplib.SMTP` with `starttls()` for the test-send step (port 587 for all three pre-built providers), and `smtplib.SMTP_SSL` is available if needed for port 465. The saved searches browser renders a Rich Table before presenting a questionary arrow-key list — the same Live-exits-before-questionary sequencing rule from Phase 1 applies here.

**Primary recommendation:** Build `config.py` first as the foundation, then wire the first-run wizard, then settings sub-pages, then the full saved searches browser. All four areas share the same questionary/Rich patterns already proven in Phase 1.

---

## Standard Stack

### Core (all already in pyproject.toml — zero new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| questionary | 2.1.1 (pinned) | All arrow-key prompts, text input, password masking, confirmations | Phase 1 established pattern; password() confirmed present |
| rich | >=13.7.0 | Panels, Tables, styled console output | Phase 1 established pattern; all existing TUI uses it |
| smtplib | stdlib | SMTP connection for test-send | Already used in report_service.py; no new dep needed |
| json | stdlib | config.json read/write | Simpler than pydantic for a flat personal config file |
| pathlib.Path | stdlib | ~/.homerfindr/config.json path management | Already used in database.py for db path |

### No New Dependencies Required

All libraries needed for Phase 2 already exist in the project. The new `homesearch/tui/config.py` uses only stdlib (`json`, `pathlib`, `os`) and existing imports.

---

## Architecture Patterns

### Recommended File Structure (new files this phase)

```
homesearch/tui/
├── config.py        # NEW — load_config() / save_config() / CONFIG_PATH constant
├── first_run.py     # NEW — run_first_run_wizard() — triggers when config absent
├── settings.py      # NEW — show_settings_menu() — CFG-01 entry point
├── smtp_wizard.py   # NEW — run_smtp_wizard() — reusable for CFG-02 and D-17
└── saved_browser.py # NEW — show_saved_searches_browser() — CFG-06 full implementation
```

Existing files modified:
- `homesearch/tui/menu.py` — wire `_handle_settings()`, `_handle_saved_searches()`, first-run check in `tui_main()`

### Pattern 1: Config Module (foundation for everything else)

**What:** Single module owns config file location, load, save, and defaults. All other new modules import from it.

**When to use:** Any read or write to `~/.homerfindr/config.json`

```python
# homesearch/tui/config.py
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".homerfindr" / "config.json"

DEFAULT_CONFIG = {
    "defaults": {
        "city": "",
        "state": "",
        "radius": 25,
        "listing_type": "sale",
        "property_types": [],
        "price_min": None,
        "price_max": None,
    },
    "smtp": {
        "provider": "",
        "server": "",
        "port": 587,
        "email": "",
        "password": "",
        "recipients": [],
    },
    "version": "1.0",
}


def config_exists() -> bool:
    return CONFIG_PATH.exists()


def load_config() -> dict:
    """Load config from disk. Returns DEFAULT_CONFIG if file missing or corrupt."""
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults so new keys added in later versions are present
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Write config to disk, creating directory if needed."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
```

### Pattern 2: First-Run Check in tui_main()

**What:** Check for config file before entering menu loop. Non-blocking if already set up.

```python
# homesearch/tui/menu.py — modified tui_main()
def tui_main():
    show_splash()
    # First-run check (D-06)
    from homesearch.tui.config import config_exists
    from homesearch.tui.first_run import run_first_run_wizard
    if not config_exists():
        run_first_run_wizard()
    run_menu_loop()
```

### Pattern 3: questionary.password() for Masked SMTP Input

**What:** questionary 2.1.1 provides `password()` — renders input as asterisks.

**Verified signature:** `questionary.password(message, default='', validate=None, style=None, **kwargs) -> Question`

```python
# homesearch/tui/smtp_wizard.py
import questionary
from homesearch.tui.styles import HOUSE_STYLE

def run_smtp_wizard(existing: dict | None = None) -> dict | None:
    """Run SMTP setup wizard. Returns smtp config dict or None if cancelled."""
    existing = existing or {}

    # D-01: Provider shortcuts auto-fill server/port
    provider = questionary.select(
        "Email provider:",
        choices=["Gmail", "Outlook/Hotmail", "Yahoo", "Custom"],
        style=HOUSE_STYLE,
    ).ask()
    if provider is None:
        return None

    PROVIDER_PRESETS = {
        "Gmail":           {"server": "smtp.gmail.com",        "port": 587},
        "Outlook/Hotmail": {"server": "smtp-mail.outlook.com", "port": 587},
        "Yahoo":           {"server": "smtp.mail.yahoo.com",   "port": 587},
        "Custom":          {"server": "",                       "port": 587},
    }
    preset = PROVIDER_PRESETS[provider]

    # D-02: Pre-filled server/port fields
    server = questionary.text(
        "SMTP server:",
        default=preset["server"],
        style=HOUSE_STYLE,
    ).ask()
    if server is None:
        return None

    port_str = questionary.text(
        "Port:",
        default=str(preset["port"]),
        style=HOUSE_STYLE,
    ).ask()
    if port_str is None:
        return None

    email = questionary.text(
        "Your email address:",
        default=existing.get("email", ""),
        style=HOUSE_STYLE,
    ).ask()
    if email is None:
        return None

    # D-02: password uses questionary.password() for masked input
    password = questionary.password(
        "App password (input masked):",
        style=HOUSE_STYLE,
    ).ask()
    if password is None:
        return None

    return {
        "provider": provider,
        "server": server,
        "port": int(port_str),
        "email": email,
        "password": password,
        "recipients": existing.get("recipients", []),
    }
```

### Pattern 4: SMTP Test-Send (D-03, D-04)

**What:** After wizard collects credentials, attempt a real SMTP connection and send. Show Rich panel for result.

```python
# In smtp_wizard.py
import smtplib
from email.mime.text import MIMEText
from rich.panel import Panel
from homesearch.tui.styles import console

def test_smtp(smtp_cfg: dict) -> bool:
    """Returns True if test email sent successfully."""
    try:
        with smtplib.SMTP(smtp_cfg["server"], smtp_cfg["port"], timeout=10) as server:
            server.starttls()
            server.login(smtp_cfg["email"], smtp_cfg["password"])
            msg = MIMEText("HomerFindr SMTP test — configuration is working!")
            msg["Subject"] = "HomerFindr: SMTP Test"
            msg["From"] = smtp_cfg["email"]
            msg["To"] = smtp_cfg["email"]
            server.sendmail(smtp_cfg["email"], smtp_cfg["email"], msg.as_string())
        return True
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")
        return False
```

### Pattern 5: Saved Searches Browser — Table + Arrow Select

**What:** Rich Table for display, then questionary.select() for row selection. Table rendered BEFORE questionary fires (Live-exits-first rule from Phase 1).

```python
# homesearch/tui/saved_browser.py
from rich.table import Table
from homesearch.tui.styles import console, HOUSE_STYLE
import questionary

def show_saved_searches_browser():
    from homesearch import database as db
    db.init_db()
    searches = db.get_saved_searches()

    if not searches:
        # D-15: empty state
        console.print("[yellow]No saved searches yet. Run a search from the main menu to save one.[/yellow]")
        return

    # D-11: Rich table renders before questionary fires
    _render_searches_table(searches)

    choices = [f"{s.name} ({s.criteria.location or 'N/A'})" for s in searches]
    choices.insert(0, "\u2190 Back")

    pick = questionary.select(
        "Select a search:",
        choices=choices,
        style=HOUSE_STYLE,
    ).ask()

    if pick is None or pick == "\u2190 Back":
        return

    idx = choices.index(pick) - 1  # -1 offset for Back entry
    _show_search_submenu(searches[idx])


def _render_searches_table(searches):
    table = Table(show_header=True, header_style="bold", show_lines=True)
    table.add_column("Name", style="white", min_width=20)
    table.add_column("Location", style="cyan", min_width=16)
    table.add_column("Last Run", style="dim", width=20)
    table.add_column("Active", justify="center", width=8)
    for s in searches:
        last_run = s.last_run_at.strftime("%Y-%m-%d %H:%M") if s.last_run_at else "Never"
        active = "[green]checkmark[/green]" if s.is_active else "[red]inactive[/red]"
        table.add_row(s.name, s.criteria.location or "N/A", last_run, active)
    console.print(table)
```

### Pattern 6: Sub-Menu with Back Navigation (D-20)

**What:** Every sub-menu places "Back" as the first choice so users are never trapped.

```python
# Consistent sub-menu pattern used throughout this phase
def _show_search_submenu(search):
    choices = ["\u2190 Back", "Run Now", "Toggle Active/Inactive", "Rename", "Delete"]
    action = questionary.select(
        f"Action for: {search.name}",
        choices=choices,
        style=HOUSE_STYLE,
    ).ask()
    # dispatch on action...
```

### Pattern 7: Delete Confirmation (D-13)

**What:** Use `questionary.confirm()` (auto_enter=True by default — Enter to confirm) for destructive actions.

```python
# D-13: delete confirmation
confirmed = questionary.confirm(
    f"Delete '{search.name}'? This cannot be undone.",
    default=False,      # Default to No — safer
    style=HOUSE_STYLE,
).ask()
if confirmed:
    from homesearch import database as db
    db.delete_search(search.id)
    console.print(f"[green]Deleted '{search.name}'.[/green]")
```

### Anti-Patterns to Avoid

- **Creating a second Rich Live inside a questionary callback:** Both take terminal ownership. Render Rich output with plain `console.print()` outside any `with Live(...):` block, THEN call any `questionary.*` function.
- **Directly mutating `settings` (pydantic-settings) for TUI config:** The `.env` + pydantic Settings object is for env-var-driven config. The new `~/.homerfindr/config.json` is for TUI preferences. They are parallel systems — never conflate them.
- **Using `questionary.text()` for port numbers without int conversion:** Port input returns a string; always `int(port_str)` before storing, wrapped in try/except for non-numeric input.
- **Blocking SMTP test on the main thread with no timeout:** `smtplib.SMTP(..., timeout=10)` prevents hanging if server unreachable. Without a timeout, test-send can freeze the CLI indefinitely.
- **Missing `parents=True` on config dir creation:** `~/.homerfindr/` may not exist on first run. Always `CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)` before writing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Masked password input | Custom character-hiding prompt | `questionary.password()` | Already ships in questionary 2.1.1 — verified present |
| SMTP connection + auth | Custom socket wrapper | `smtplib.SMTP` with `starttls()` | stdlib; already used in `report_service.py` |
| Config file defaults/merging | Complex schema validator | Simple `dict.update()` merge on load | Config is shallow and personal-tool simple; no ORM needed |
| Arrow-key list navigation | Curses-based terminal UI | `questionary.select()` | Phase 1 established; style already shared via `HOUSE_STYLE` |
| Database CRUD for saved searches | New DB layer | `database.py` existing functions | `get_saved_searches()`, `update_search()`, `delete_search()` are all already implemented and confirmed |

**Key insight:** Every hard problem in this phase is already solved — SMTP is in `report_service.py`, database CRUD is in `database.py`, and TUI primitives are in questionary. This phase is primarily wiring and new UI screens, not new infrastructure.

---

## Common Pitfalls

### Pitfall 1: Rich Live / questionary Terminal Ownership Conflict
**What goes wrong:** If Rich Live is still active when `questionary.select()` fires, terminal output is corrupted — garbled characters, double rendering, cursor in wrong position.
**Why it happens:** Both libraries claim raw terminal input. questionary uses prompt_toolkit; Rich Live uses its own render loop.
**How to avoid:** Always print Rich Table/Panel output with plain `console.print()` (not inside a `with Live(...):` block) before calling any `questionary.*` function. If a spinner is running, it must fully exit the `with Live(...)` context before prompting.
**Warning signs:** Garbled text, prompt appearing mid-table, cursor jumping around.

### Pitfall 2: config.json None Values and Type Handling
**What goes wrong:** `json.dumps({"price_min": None})` correctly serializes to `"price_min": null`. Reading it back gives Python `None`. The risk is accidentally using string comparisons against config values.
**Why it happens:** Verified: `json.loads('{"x": null}')` returns `{"x": None}` correctly. The risk is accidentally using `str(value)` comparisons.
**How to avoid:** Always access config values with `config.get("key")` and treat `None` as "not set". Use `if config.get("key") is None` not string comparison.

### Pitfall 3: SMTP Test-Send Hangs Without Timeout
**What goes wrong:** If the user enters a wrong server hostname, `smtplib.SMTP(server, port)` blocks indefinitely waiting for a TCP connection.
**Why it happens:** Default socket timeout in smtplib is None (infinite).
**How to avoid:** Always pass `timeout=10` to `smtplib.SMTP(server, port, timeout=10)`.
**Warning signs:** CLI appears frozen after the test-send prompt — no spinner, no error.

### Pitfall 4: questionary.select() default= Value Must Match a Choice Exactly
**What goes wrong:** If you pass `default="25 miles"` but the choice label is `"25"`, questionary silently ignores the default and highlights the first item instead.
**Why it happens:** questionary matches `default` by equality against the `Choice.value` (or the string itself if no `.value` is set).
**How to avoid:** When setting defaults for arrow-key selects, use `questionary.Choice(title="25 miles", value=25)` and pass `default=25` (the value, not the display title), or ensure `default` exactly matches the string in `choices`.

### Pitfall 5: Saving Config Mid-Wizard on Interrupt Leaves Partial State
**What goes wrong:** If user presses Ctrl+C partway through the first-run wizard, config.json may be written with partial data.
**Why it happens:** If `save_config()` is called after each step rather than at the end.
**How to avoid:** Collect all wizard answers in a local dict first, then call `save_config()` once at the end of the wizard. Wrap wizard entry in `try/except KeyboardInterrupt` and do NOT save on interrupt — let the wizard re-run on next launch.

### Pitfall 6: Phase 1 _handle_saved_searches() Stub Has Partial Logic
**What goes wrong:** The existing `_handle_saved_searches()` in menu.py already runs a basic search-and-run flow (lines 67-96), but lacks the full browser (no table, no sub-menu, no toggle/rename/delete). Patching around it creates confusion.
**How to avoid:** Replace `_handle_saved_searches()` body entirely with a delegation call to `saved_browser.show_saved_searches_browser()`. Do not try to extend the existing stub logic.

---

## Code Examples

### Verified: questionary.password() — masked input
```python
# Verified via introspection of questionary 2.1.1
import questionary
from homesearch.tui.styles import HOUSE_STYLE

password = questionary.password(
    "App password (input masked):",
    style=HOUSE_STYLE,
).ask()
# Returns str or None (None if user pressed Ctrl+C)
```

### Verified: questionary.confirm() — delete confirmation
```python
# Verified via introspection of questionary 2.1.1
confirmed = questionary.confirm(
    "Delete 'My Dallas Search'? This cannot be undone.",
    default=False,
    style=HOUSE_STYLE,
).ask()
# Returns bool or None
```

### Verified: smtplib starttls pattern (matches report_service.py existing usage)
```python
# Matches homesearch/services/report_service.py lines 152-156
import smtplib
with smtplib.SMTP(server, port, timeout=10) as smtp:
    smtp.starttls()
    smtp.login(email, password)
    smtp.sendmail(email, recipient, msg.as_string())
```

### Verified: config.json load with merge-defaults
```python
# Python stdlib json — verified round-trip with None/null values
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".homerfindr" / "config.json"

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)  # Corrupt config: return defaults, do not crash

def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
```

### Verified: Rich Table for saved searches display
```python
# Rich 13.7 API verified via introspection
from rich.table import Table
from homesearch.tui.styles import console

table = Table(show_header=True, header_style="bold", show_lines=True)
table.add_column("Name", style="white", min_width=20)
table.add_column("Location", style="cyan", min_width=16)
table.add_column("Last Run", style="dim", width=20)
table.add_column("Active", justify="center", width=8)
# add_row() calls follow
console.print(table)  # Must fully complete BEFORE any questionary call
```

---

## Integration Map

| Integration Point | From | To | How |
|-------------------|------|----|-----|
| First-run trigger | `menu.py:tui_main()` | `first_run.py:run_first_run_wizard()` | `if not config_exists(): run_first_run_wizard()` before `run_menu_loop()` |
| Settings entry | `menu.py:_handle_settings()` | `settings.py:show_settings_menu()` | Replace stub body with delegation call |
| Saved searches entry | `menu.py:_handle_saved_searches()` | `saved_browser.py:show_saved_searches_browser()` | Replace existing stub body entirely |
| SMTP wizard reuse | `settings.py:Email Settings` | `smtp_wizard.py:run_smtp_wizard()` | Import and call with `existing=config["smtp"]` |
| Run Now | `saved_browser.py` | `results.py:execute_search_with_spinner()` + `display_results()` | Same import pattern as existing `_handle_new_search()` |
| Config read | All new TUI modules | `config.py:load_config()` | Single import; no module caches config — always read fresh |
| Config write | All new TUI modules | `config.py:save_config(config)` | Load then mutate then save pattern |
| Database CRUD | `saved_browser.py` | `database.py` | `db.update_search(id, is_active=...)`, `db.delete_search(id)`, `db.update_search(id, name=...)` |

---

## SMTP Provider Presets (D-01 verified values)

| Provider | Server | Port | Auth Note |
|----------|--------|------|-----------|
| Gmail | smtp.gmail.com | 587 | Requires App Password if 2FA enabled |
| Outlook/Hotmail | smtp-mail.outlook.com | 587 | Standard account password |
| Yahoo | smtp.mail.yahoo.com | 587 | Requires App Password |
| Custom | (user input) | 587 (default) | User sets all fields |

All four use STARTTLS on port 587. `smtplib.SMTP_SSL` (port 465) is available in stdlib — can be a future enhancement without code rework since the wizard collects port as a text field.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Store SMTP creds in .env only | JSON config at ~/.homerfindr/config.json | Parallel systems — .env for env-var automation, JSON for TUI interactive config |
| Phase 1 saved searches: basic run-only | Phase 2: full browser with toggle/rename/delete | _handle_saved_searches() stub gets replaced |

---

## Open Questions

1. **Config migration when schema changes**
   - What we know: Claude's discretion (no locked decision)
   - What's unclear: Whether to version-check on load and add missing keys, or always full-overwrite
   - Recommendation: Use the merge-with-defaults pattern in `load_config()` (always deep-merge loaded data over DEFAULT_CONFIG) — new keys in future versions auto-populate from defaults without breaking existing configs

2. **Corrupt config behavior**
   - What we know: Claude's discretion
   - What's unclear: Silent fallback vs. user-visible warning
   - Recommendation: On `JSONDecodeError`, print a dim warning `[dim]Config file unreadable — using defaults.[/dim]` then proceed. Do NOT crash or block startup.

3. **Gmail App Password guidance**
   - What we know: Gmail requires App Passwords when 2FA is enabled; standard account password fails with SMTP
   - Recommendation: After provider selection, display a dim hint: `[dim]Gmail tip: Use an App Password from myaccount.google.com/apppasswords[/dim]`

---

## Sources

### Primary (HIGH confidence)
- questionary 2.1.1 — verified via `uv run python` introspection — `password()`, `text()`, `select()`, `confirm()` signatures confirmed
- Python stdlib `smtplib`, `json`, `pathlib` — verified via Python 3.11 introspection; behavior matches existing `report_service.py` usage
- `homesearch/tui/menu.py` — integration stubs read directly; both `_handle_settings()` and `_handle_saved_searches()` confirmed present
- `homesearch/tui/styles.py` — HOUSE_STYLE and console confirmed present
- `homesearch/database.py` — all CRUD functions read directly; `update_search(**kwargs)` and `delete_search(id)` confirmed
- `homesearch/services/report_service.py` — `smtplib.SMTP` + `starttls()` pattern verified in existing code

### Secondary (MEDIUM confidence)
- SMTP provider server/port values (Gmail, Outlook, Yahoo) — well-established public knowledge; STARTTLS on 587 is standard for all three

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified via runtime introspection; no new dependencies
- Architecture: HIGH — all integration points located in source code; patterns directly extend Phase 1
- Pitfalls: HIGH — Rich/questionary conflict is a documented Phase 1 constraint; SMTP timeout is verified stdlib behavior
- SMTP provider presets: MEDIUM — values are well-known; not verified by sending actual test email in this research session

**Research date:** 2026-03-25
**Valid until:** 2026-06-25 (questionary 2.1.1 is pinned; stdlib will not change)
