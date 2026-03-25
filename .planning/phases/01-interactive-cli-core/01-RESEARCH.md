# Phase 1: Interactive CLI Core - Research

**Researched:** 2026-03-25
**Domain:** Python interactive CLI — questionary, Rich, art, threading, FastAPI lifespan
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Large ASCII art house with "HomerFindr" title rendered via `art` library (677+ fonts), colored with Rich gradient (green → cyan)
- **D-02:** Typewriter-style reveal animation (Rich Live context), displays for ~2 seconds, then clears to main menu
- **D-03:** Splash shows on every launch — it's the brand moment, keep it fast enough to not annoy
- **D-04:** Arrow pointer (►) with highlighted/inverted background for selected item — questionary select prompts
- **D-05:** Green/cyan accent colors on dark terminal background — consistent house theme throughout
- **D-06:** Main menu options in order: 🏠 New Search, 📋 Saved Searches, ⚙️ Settings, 🌐 Launch Web UI, 🚪 Exit
- **D-07:** After any action completes, return to main menu (loop until Exit or Ctrl+C)
- **D-08:** City/State or ZIP code is the ONLY field requiring keyboard typing — everything else is arrow-selectable
- **D-09:** Field order follows the existing wizard: Type → Property → Location → Radius → ZIP Discovery → Price → Beds → Baths → Sqft → Lot → Year → Floors → Basement → Garage → HOA
- **D-10:** Each optional field shows "(Enter to skip)" hint — pressing Enter with no selection skips the field
- **D-11:** Price, sqft, lot size use pre-built range options (e.g., "$200k-$300k", "$300k-$400k") not free typing
- **D-12:** At the end of wizard, show search summary panel and confirm: "Search now?" (Yes/No/Edit)
- **D-13:** Rich table with colored columns: Price (green), Beds/Baths (cyan), Sqft (yellow), Address (white)
- **D-14:** Results count header: "Found 47 listings across 2 providers"
- **D-15:** Arrow keys to scroll through results, Enter on a row opens the listing URL in default browser
- **D-16:** After viewing results: "Save this search?" prompt, then return to main menu
- **D-17:** Search runs on a background thread (threading.Thread) so Rich spinner stays animated
- **D-18:** Rich spinner with house emoji: "🏠 Searching Realtor.com..." then "🏠 Searching Redfin..."
- **D-19:** If a provider fails/403s, show warning but continue with other providers' results

### Claude's Discretion

- Exact ASCII art font choice (from art library's 677+ options)
- Spinner animation style (dots, line, bounce — whatever looks best with Rich)
- Exact color hex values within the green/cyan theme
- Table column widths and truncation behavior
- Error message wording

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIX-02 | Fix FastAPI startup deprecation warnings (lifespan migration) | FastAPI lifespan pattern documented in Architecture Patterns section — must be done first to prevent warning output corrupting Rich terminal |
| CLI-01 | ASCII art house-themed splash screen with gradient colors on launch | art 6.5 + Rich Console gradient confirmed; terminal-width safety with os.get_terminal_size() documented |
| CLI-02 | Animated loading sequence with house/building ASCII art during startup | Rich Live context typewriter pattern documented; must exit Live before questionary prompts fire |
| CLI-03 | Arrow-key main menu with options: New Search, Saved Searches, Settings, Launch Web UI, Exit | questionary.select() pattern with custom style documented; menu loop pattern provided |
| CLI-04 | Arrow-key search wizard — all 15 fields navigable with arrows + Enter only | questionary select/checkbox/confirm per-field patterns documented; field order and skip behavior specified |
| CLI-05 | Pre-built option lists for every search field (no free typing required) | All 15 SearchCriteria fields mapped to questionary prompt types and pre-built option lists |
| CLI-06 | Animated search progress with Rich spinners/progress bars while scraping providers | Rich Live + threading.Event pattern for non-blocking spinner documented |
| CLI-07 | Non-blocking search execution (background thread) so CLI stays responsive | threading.Thread pattern with event signaling documented; critical sequencing with Rich Live |
| CLI-08 | Colorful search results display with Rich tables/panels showing key property details | Rich Table with per-column styles + webbrowser.open for URL launch documented |
| CLI-09 | Return to main menu after any action completes | While-loop menu structure pattern documented; KeyboardInterrupt handling included |
</phase_requirements>

---

## Summary

Phase 1 replaces the existing Typer/Rich.Prompt CLI (`homesearch/main.py`) with a fully interactive arrow-key experience. The existing service layer (`search_service.py`, `zip_service.py`, `database.py`) is reused unchanged — only the CLI surface layer is replaced. The two new libraries required are `questionary` (arrow-key select prompts) and `art` (ASCII art). Rich is already installed and extends naturally to handle spinners, tables, panels, and the splash animation.

The single most important sequencing rule: **Rich's Live context must be fully exited before any questionary prompt fires.** Rich's Live display and questionary's prompt_toolkit input handling both take ownership of the terminal. Running them concurrently corrupts output. The correct pattern is sequential: (1) exit Live, (2) start questionary prompt, (3) receive value, (4) optionally re-enter Live for display. This rule governs the splash animation, the search spinner, and every results display.

The FastAPI deprecation fix (FIX-02) must be the first task in this phase. The `@app.on_event("startup")` in `homesearch/api/routes.py` emits a deprecation warning that leaks into the terminal when the CLI is launched. Since the new CLI takes ownership of Rich's terminal early, any stray warning output before that point corrupts the splash screen render.

**Primary recommendation:** Replace `homesearch/main.py` with a `tui_main()` function that drives a `while True` questionary menu loop. Extract the search wizard, results display, and splash into focused helper modules under `homesearch/tui/`. Keep all service calls identical to what `main.py` currently does — only the input/output surface changes.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| questionary | 2.1.1 | Arrow-key select, checkbox, confirm, text prompts | Actively maintained (Aug 2025 release), built on prompt_toolkit 3, Python 3.9–3.14, clean API. InquirerPy is inactive/abandoned per Snyk. |
| art | 6.5 | Text-to-ASCII-art for splash screen | 677+ fonts, one-call API (`text2art()`), MIT, Apr 2025 release. Simpler than pyfiglet for this use case. |
| Rich | >=13.7.0 | Already installed — Terminal styling, tables, panels, Live, Progress, spinner | Already in stack. Handles all display output after questionary prompts return. |
| threading | stdlib | Non-blocking search execution | Standard library threading.Thread with daemon=True; no new dependency needed. |
| webbrowser | stdlib | Open listing URLs in default browser | Standard library, cross-platform. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| os.get_terminal_size() | stdlib | Terminal width detection before rendering ASCII art | Always call before `text2art()` to prevent art overflow on narrow terminals |
| signal | stdlib | Ctrl+C handling in menu loop | Register SIGINT handler to ensure clean exit from the while loop |

### Not Needed / Rejected
| Instead of | Why Rejected |
|------------|-------------|
| InquirerPy | Classified Inactive by Snyk, no PyPI release since 2022, unresolved issues |
| Textual | Full-screen TUI framework — overkill for sequential prompt flow; takes over entire terminal |
| simple-term-menu | Linux-primary, curses-based, less Rich integration polish on macOS |
| pyfiglet | Fewer fonts (100 vs 677+), slightly more complex API than art for this use case |

**Installation (new dependencies only):**
```bash
pip install "questionary>=2.1.1" "art>=6.5"
```

Add to `pyproject.toml` `[project.dependencies]`:
```toml
"questionary>=2.1.1",
"art>=6.5",
```

**Version verification:** questionary 2.1.1 confirmed on PyPI (Aug 28 2025). art 6.5 confirmed on PyPI (Apr 12 2025). Rich >=13.7.0 already declared in pyproject.toml.

---

## Architecture Patterns

### Recommended Project Structure

The cleanest approach is a new `homesearch/tui/` package for the interactive layer. This keeps `main.py` as a thin entry-point dispatcher and isolates all TUI code from the existing CLI command structure.

```
homesearch/
├── main.py                  # Entry point: dispatch to tui_main() or legacy Typer commands
├── tui/
│   ├── __init__.py
│   ├── splash.py            # ASCII art splash + typewriter animation
│   ├── menu.py              # Main menu loop (questionary.select while-loop)
│   ├── wizard.py            # 15-field search wizard (questionary per field)
│   ├── results.py           # Rich table results display + URL open
│   └── styles.py            # Shared questionary Style objects and Rich color constants
├── api/
│   └── routes.py            # CHANGE: migrate @app.on_event to lifespan (FIX-02)
└── services/                # UNCHANGED — all search/zip/db logic stays here
```

### Pattern 1: FIX-02 — FastAPI Lifespan Migration

**What:** Replace `@app.on_event("startup")` with the `lifespan` context manager.

**When to use:** First task of this phase, before any CLI work. The deprecation warning leaks into terminal output.

```python
# Source: FastAPI official docs — https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI
from homesearch import database as db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.init_db()
    yield
    # Shutdown (add stop_scheduler here in Phase 2)

app = FastAPI(title="HomeSearch API", version="0.1.0", lifespan=lifespan)
# Remove the old @app.on_event("startup") entirely
```

### Pattern 2: Splash Screen (art + Rich Live typewriter)

**What:** Render ASCII art with a typewriter reveal animation, then clear to main menu.

**Critical rule:** Exit the `Live` context fully before starting any questionary prompt.

```python
# Source: Rich docs — https://rich.readthedocs.io/en/latest/live.html
import time
from art import text2art
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
import os

console = Console()

def show_splash():
    cols = os.get_terminal_size().columns
    ascii_art = text2art("HomerFindr", font="banner3-D")
    # Fallback for narrow terminals
    if len(ascii_art.splitlines()[0]) > cols - 4:
        ascii_art = text2art("HomerFindr", font="small")

    lines = ascii_art.splitlines()
    rendered = Text()

    with Live(console=console, refresh_per_second=20) as live:
        for line in lines:
            rendered.append(line + "\n", style="bold cyan")
            live.update(Panel(rendered, border_style="green", title="[bold green]HomerFindr[/bold green]"))
            time.sleep(0.04)  # typewriter delay per line
        time.sleep(1.8)  # hold splash before clearing
    # Live context exited — safe to call questionary now
    console.clear()
```

### Pattern 3: questionary Main Menu Loop

**What:** `while True` loop with `questionary.select()`. Returns to menu after every action.

**Critical rule:** Always call `questionary.select().ask()` only after any Rich Live/Progress context is fully exited (the `with` block has closed).

```python
# Source: questionary docs — https://questionary.readthedocs.io/en/stable/pages/types.html
import questionary
from questionary import Style

HOUSE_STYLE = Style([
    ("qmark",    "fg:#00FF7F bold"),      # green question mark
    ("question", "fg:#00CED1 bold"),      # cyan question text
    ("pointer",  "fg:#00FF7F bold"),      # green arrow pointer ►
    ("highlighted", "fg:#000000 bg:#00CED1 bold"),  # inverted cyan selection
    ("selected", "fg:#00FF7F"),
    ("answer",   "fg:#00FF7F bold"),
])

def run_menu_loop():
    while True:
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "🏠  New Search",
                "📋  Saved Searches",
                "⚙️   Settings",
                "🌐  Launch Web UI",
                "🚪  Exit",
            ],
            style=HOUSE_STYLE,
        ).ask()

        if choice is None or "Exit" in choice:
            console.print("[bold cyan]Goodbye! 🏠[/bold cyan]")
            break
        elif "New Search" in choice:
            run_search_wizard()
        elif "Saved Searches" in choice:
            show_saved_searches()
        elif "Settings" in choice:
            show_settings()          # Phase 2
        elif "Launch Web UI" in choice:
            launch_web_ui()          # Phase 4 — stub for now
```

### Pattern 4: Search Wizard — questionary per field

**What:** Each of the 15 SearchCriteria fields maps to a questionary prompt type. Fields with natural option lists use `select`. Yes/No/Don't-care fields use `select` with three options. Numeric ranges use `select` with pre-built labels. City/ZIP is the only `text` prompt.

```python
# Source: questionary docs — https://questionary.readthedocs.io/en/stable/pages/types.html
import questionary

def run_search_wizard() -> SearchCriteria | None:
    # 1. Listing type — select
    listing_type_str = questionary.select(
        "What are you looking for?",
        choices=["For Sale", "For Rent", "Recently Sold"],
        style=HOUSE_STYLE,
    ).ask()
    if listing_type_str is None:
        return None  # User Ctrl+C'd

    # 2. Property type — select
    property_type_str = questionary.select(
        "Property type?",
        choices=["Any", "Single Family", "Condo", "Townhouse", "Multi-Family", "Land"],
        style=HOUSE_STYLE,
    ).ask()

    # 3. Location — text (ONLY free-typing field)
    location = questionary.text(
        "City, State or ZIP code:",
        style=HOUSE_STYLE,
    ).ask()
    if not location or not location.strip():
        return None

    # 4. Radius — select with pre-built options
    radius_str = questionary.select(
        "Search radius?",
        choices=["5 miles", "10 miles", "25 miles", "50 miles", "100 miles"],
        default="25 miles",
        style=HOUSE_STYLE,
    ).ask()
    radius = int(radius_str.split()[0])

    # 5. Price range — select, Enter to skip
    price_choice = questionary.select(
        "Price range? (arrow to select, Enter to skip)",
        choices=[
            "Any",
            "Under $200k",
            "$200k – $300k",
            "$300k – $400k",
            "$400k – $500k",
            "$500k – $750k",
            "$750k – $1M",
            "Over $1M",
        ],
        style=HOUSE_STYLE,
    ).ask()
    price_min, price_max = _parse_price_range(price_choice)

    # 6. Beds min — select, Any = no filter
    beds_str = questionary.select(
        "Minimum bedrooms?",
        choices=["Any", "1+", "2+", "3+", "4+", "5+"],
        style=HOUSE_STYLE,
    ).ask()
    beds_min = None if beds_str == "Any" else int(beds_str[0])

    # 7. Baths min — select
    baths_str = questionary.select(
        "Minimum bathrooms?",
        choices=["Any", "1+", "1.5+", "2+", "3+"],
        style=HOUSE_STYLE,
    ).ask()
    baths_min = None if baths_str == "Any" else float(baths_str.rstrip("+"))

    # 8–9. Sqft range — select
    sqft_choice = questionary.select(
        "Square footage range?",
        choices=["Any", "Under 1,000", "1,000–1,500", "1,500–2,000",
                 "2,000–3,000", "3,000–4,000", "Over 4,000"],
        style=HOUSE_STYLE,
    ).ask()
    sqft_min, sqft_max = _parse_sqft_range(sqft_choice)

    # 10–11. Lot size range — select
    lot_choice = questionary.select(
        "Lot size range?",
        choices=["Any", "Under 5,000 sqft", "5,000–10,000 sqft",
                 "10,000–20,000 sqft", "Over 20,000 sqft"],
        style=HOUSE_STYLE,
    ).ask()
    lot_min, lot_max = _parse_lot_range(lot_choice)

    # 12–13. Year built range — select
    year_choice = questionary.select(
        "Year built?",
        choices=["Any", "2020+", "2010+", "2000+", "1990+", "1980+", "1970 or older"],
        style=HOUSE_STYLE,
    ).ask()
    year_min = _parse_year(year_choice)

    # 14. Stories — select
    stories_str = questionary.select(
        "Minimum floors/stories?",
        choices=["Any", "1+", "2+"],
        style=HOUSE_STYLE,
    ).ask()
    stories_min = None if stories_str == "Any" else int(stories_str[0])

    # 15. Basement — select
    basement_str = questionary.select(
        "Basement?",
        choices=["Don't care", "Required", "Not wanted"],
        style=HOUSE_STYLE,
    ).ask()
    has_basement = {"Required": True, "Not wanted": False}.get(basement_str)

    # 16. Garage — select
    garage_str = questionary.select(
        "Garage?",
        choices=["Don't care", "Required", "Not wanted"],
        style=HOUSE_STYLE,
    ).ask()
    has_garage = {"Required": True, "Not wanted": False}.get(garage_str)

    # 17. HOA max — select
    hoa_choice = questionary.select(
        "Max monthly HOA?",
        choices=["Any / No limit", "No HOA ($0)", "Up to $100/mo",
                 "Up to $200/mo", "Up to $500/mo"],
        style=HOUSE_STYLE,
    ).ask()
    hoa_max = _parse_hoa(hoa_choice)

    return SearchCriteria(
        location=location.strip(),
        radius_miles=radius,
        listing_type=_map_listing_type(listing_type_str),
        property_types=_map_property_type(property_type_str),
        price_min=price_min,
        price_max=price_max,
        bedrooms_min=beds_min,
        bathrooms_min=baths_min,
        sqft_min=sqft_min,
        sqft_max=sqft_max,
        lot_sqft_min=lot_min,
        lot_sqft_max=lot_max,
        year_built_min=year_min,
        stories_min=stories_min,
        has_basement=has_basement,
        has_garage=has_garage,
        hoa_max=hoa_max,
    )
```

### Pattern 5: Non-Blocking Search with Rich Spinner (threading)

**What:** Run `search_service.run_search()` in a background thread. Use Rich Live + spinner on the main thread so the animation stays smooth. Signal completion with `threading.Event`.

**Critical sequencing:** The questionary wizard must fully complete and return before the Live spinner starts. Live must fully exit before questionary prompts fire again.

```python
# Source: Rich docs — https://rich.readthedocs.io/en/latest/spinner.html
#         Python stdlib threading docs
import threading
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from homesearch.services.search_service import run_search, get_providers

def execute_search_with_spinner(criteria: SearchCriteria) -> list:
    results: list = []
    error: list = []
    done_event = threading.Event()

    def _search_thread():
        try:
            results.extend(run_search(criteria, use_zip_discovery=True))
        except Exception as e:
            error.append(e)
        finally:
            done_event.set()

    thread = threading.Thread(target=_search_thread, daemon=True)
    thread.start()

    provider_names = [p.name for p in get_providers()]
    status_text = Text()

    with Live(console=console, refresh_per_second=10) as live:
        idx = 0
        while not done_event.is_set():
            current_provider = provider_names[idx % len(provider_names)]
            live.update(Text(f"🏠  Searching {current_provider}...", style="bold cyan"))
            done_event.wait(timeout=0.3)
            idx += 1

    # Live fully exited — safe to display results with console.print
    thread.join(timeout=0.5)

    if error:
        console.print(f"[yellow]Warning: search error — {error[0]}[/yellow]")

    return results
```

### Pattern 6: Results Display with URL Launch

**What:** Rich table with per-column styles. questionary select over results to open URL.

```python
# Source: Rich docs — https://rich.readthedocs.io/en/latest/tables.html
import webbrowser
from rich.table import Table
from rich.panel import Panel

def display_results(results: list, provider_count: int):
    if not results:
        console.print("[yellow]No properties found matching your criteria.[/yellow]")
        return

    console.print(Panel(
        f"[bold green]Found {len(results)} listings across {provider_count} providers[/bold green]",
        border_style="green",
    ))

    table = Table(show_header=True, header_style="bold", show_lines=True,
                  expand=False, row_styles=["", "dim"])
    table.add_column("#",       style="dim",         width=4)
    table.add_column("Address", style="white",       min_width=28, no_wrap=True)
    table.add_column("Price",   style="green",       justify="right", width=12)
    table.add_column("Bed/Ba",  style="cyan",        justify="center", width=8)
    table.add_column("SqFt",    style="yellow",      justify="right", width=8)
    table.add_column("Yr",      style="dim",         justify="center", width=6)
    table.add_column("Source",  style="dim",         width=10)

    display = results[:50]
    for i, l in enumerate(display, 1):
        price_str = f"${l.price:,.0f}" if l.price else "—"
        bed_bath  = f"{l.bedrooms or '?'}/{l.bathrooms or '?'}"
        sqft_str  = f"{l.sqft:,}" if l.sqft else "—"
        table.add_row(
            str(i),
            l.address[:40] + ("…" if len(l.address) > 40 else ""),
            price_str,
            bed_bath,
            sqft_str,
            str(l.year_built or "—"),
            l.source,
        )
    console.print(table)

    # Arrow-key selection to open URL
    url_map = {f"{i}. {display[i-1].address[:40]}": display[i-1].source_url
               for i in range(1, len(display) + 1) if display[i-1].source_url}
    if url_map:
        choice = questionary.select(
            "Select a listing to open in browser (or press Ctrl+C to skip):",
            choices=list(url_map.keys()) + ["↩  Back to menu"],
            style=HOUSE_STYLE,
        ).ask()
        if choice and "Back to menu" not in choice and choice in url_map:
            webbrowser.open(url_map[choice])
```

### Anti-Patterns to Avoid

- **Running Rich Live while questionary is active:** Corrupts terminal. Always exit `with Live(...)` fully before calling `.ask()`.
- **Calling `uvicorn.run()` from the main CLI thread:** Blocking; conflicts with prompt_toolkit loop. Phase 4 concern, but stub in the menu must not call `uvicorn.run()` directly.
- **Using `Prompt.ask()` from Rich for search fields:** This is the old pattern. All search fields must use `questionary.select()` or `questionary.confirm()`.
- **Forgetting `questionary.select().ask()` return can be `None`:** Returns `None` on Ctrl+C/keyboard interrupt. Every `.ask()` call must check for `None` before using the result.
- **Not checking terminal width before art render:** Art output can be 80–120+ chars wide. On narrow terminals it wraps mid-character and looks broken.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Arrow-key menus | Custom curses/readline menu | `questionary.select()` | questionary handles cursor positioning, ANSI codes, keyboard events, macOS Terminal.app vs iTerm2 differences |
| ASCII art generation | String art drawn by hand | `art.text2art()` | 677+ fonts, handles character sizing, one-call API |
| Spinner animation | Custom `\|/-\` spinner loop | `Rich.Live` + `Rich.Spinner` | Rich handles terminal refresh rate, ANSI codes, thread-safe rendering |
| Terminal-width detection | Manual `shutil.get_terminal_size()` logic | `os.get_terminal_size().columns` with try/except | Built-in; handles piped stdout gracefully |
| URL opening | subprocess browser invocation | `webbrowser.open()` | Cross-platform stdlib, handles macOS/Linux/Windows |
| Non-blocking search | `asyncio` with async providers | `threading.Thread(daemon=True)` | Providers are synchronous (homeharvest, redfin). asyncio doesn't help with sync code. Threading is the correct tool. |

**Key insight:** All the hard terminal interaction problems (cursor management, ANSI codes, keyboard scanning) are solved by questionary + Rich. Any custom solution will break on edge-case terminals.

---

## Common Pitfalls

### Pitfall 1: Rich Live + questionary running simultaneously
**What goes wrong:** Both take ownership of terminal cursor/output stream. Output is corrupted: garbled lines, cursor left in wrong position, subsequent prints appear at wrong indentation.
**Why it happens:** Rich `Live` holds terminal in a managed render state. questionary/prompt_toolkit independently redraws the prompt. Neither knows about the other's line-count bookkeeping.
**How to avoid:** Strict sequential rule — exit `with Live(...):` block fully before any `.ask()` call. Use `console.clear()` between splash and menu. Never call `console.print()` inside an active questionary prompt callback.
**Warning signs:** Cursor appears in wrong position after menu selection. Blank lines appear between prompts.

### Pitfall 2: Blocking search thread freezes spinner
**What goes wrong:** `run_search()` calls synchronous homeharvest/redfin providers with `time.sleep()` between ZIPs. If called on the main thread, the Rich spinner animation freezes immediately.
**Why it happens:** homeharvest enforces a 1.5s sleep per ZIP. 25 ZIPs = ~38 seconds of blocking. Rich's `Live` refresh loop runs on the main thread and cannot update during blocking I/O.
**How to avoid:** Always wrap `run_search()` in `threading.Thread(target=..., daemon=True)`. Use `threading.Event` to signal completion. Poll `done_event.wait(timeout=0.3)` inside the Live loop.
**Warning signs:** Spinner shows for 0.5 seconds then freezes the moment search starts.

### Pitfall 3: questionary `.ask()` returns None on Ctrl+C
**What goes wrong:** User presses Ctrl+C during a questionary prompt. `.ask()` returns `None`. Code tries to use the `None` value (e.g., `choice.split()`) and raises `AttributeError`.
**Why it happens:** questionary catches `KeyboardInterrupt` internally and returns `None` rather than propagating the exception.
**How to avoid:** Every `.ask()` call must guard: `if choice is None: return`. In the menu loop, `None` should trigger clean exit.
**Warning signs:** Traceback on Ctrl+C mid-wizard showing `AttributeError: 'NoneType' has no attribute ...`.

### Pitfall 4: FastAPI deprecation warning leaks into splash screen
**What goes wrong:** `@app.on_event("startup")` in `routes.py` emits a deprecation warning. When the CLI later launches the server (Phase 4), this warning appears in the terminal, breaking Rich's layout.
**Why it happens:** FastAPI's `on_event` decorator has been deprecated since FastAPI 0.93. The deprecation warning goes to stderr, which Rich does not intercept.
**How to avoid:** Migrate to `lifespan` context manager as the first task of this phase. Even if the web server isn't launched in Phase 1, the fix eliminates the warning from any future import path.
**Warning signs:** Warning text "DeprecationWarning: on_event is deprecated..." appears in terminal output.

### Pitfall 5: ASCII art overflow on narrow terminals
**What goes wrong:** `text2art("HomerFindr", font="banner3-D")` renders at ~90 characters wide. On an 80-column terminal (macOS Terminal.app default, tmux split panes), the art wraps mid-character. The result looks like visual noise, not a splash screen.
**Why it happens:** figlet/art fonts are fixed-width per character. "HomerFindr" (10 chars) at many font sizes exceeds 80 columns.
**How to avoid:** Query `os.get_terminal_size().columns` before rendering. If art width > terminal width - 4, fall back to a shorter font (e.g., `"small"` or `"banner"`). Wrap art render in `try/except (OSError, UnicodeEncodeError)` for piped stdout fallback.
**Warning signs:** Art output has line breaks in unexpected places. Unicode encoding errors on `LANG=C` systems.

### Pitfall 6: Wizard field count mismatch with SearchCriteria
**What goes wrong:** The existing `SearchCriteria` model has 15 distinct filter concepts. The decisions specify field order and "Enter to skip" behavior. If a wizard field is omitted or mapped to the wrong model field, searches silently use wrong criteria.
**Why it happens:** The mapping between human-readable option labels ("$200k–$300k") and model values (`price_min=200000, price_max=300000`) must be explicit. It's easy to miss edge cases (e.g., "Any" maps to `None`, not `0`).
**How to avoid:** Write explicit `_parse_*` helper functions for each range field. Test each mapping manually before integration. Ensure "Any" / "Don't care" always produces `None` in the model (never `0` or `False`).
**Warning signs:** Search returns 0 results when user selects "Any" for a filter (filter `None` check failed).

---

## Code Examples

### Verified Pattern: questionary Style Object
```python
# Source: questionary docs https://questionary.readthedocs.io/en/stable/pages/style.html
from questionary import Style

HOUSE_STYLE = Style([
    ("qmark",       "fg:#00FF7F bold"),
    ("question",    "fg:#00CED1 bold"),
    ("pointer",     "fg:#00FF7F bold"),
    ("highlighted", "fg:#000000 bg:#00CED1 bold"),
    ("selected",    "fg:#00FF7F"),
    ("answer",      "fg:#00FF7F bold"),
])
```

### Verified Pattern: questionary select with skip option
```python
# Source: questionary docs https://questionary.readthedocs.io/en/stable/pages/types.html
choice = questionary.select(
    "Minimum bedrooms? (select Any to skip)",
    choices=["Any", "1+", "2+", "3+", "4+", "5+"],
    default="Any",
    style=HOUSE_STYLE,
).ask()
# Returns None on Ctrl+C — always check
beds_min = None if (choice is None or choice == "Any") else int(choice[0])
```

### Verified Pattern: art text2art with fallback
```python
# Source: art library README https://github.com/sepandhaghighi/art
import os
from art import text2art

def make_splash_art(text: str, preferred_font: str = "banner3-D") -> str:
    try:
        cols = os.get_terminal_size().columns
    except OSError:
        cols = 80  # fallback for piped stdout

    art_str = text2art(text, font=preferred_font)
    # Check first line width
    if art_str and len(art_str.splitlines()[0]) > cols - 4:
        art_str = text2art(text, font="small")
    return art_str
```

### Verified Pattern: Rich Live + threading.Event for non-blocking spinner
```python
# Source: Rich docs https://rich.readthedocs.io/en/latest/live.html
#         Python threading docs
import threading
from rich.live import Live
from rich.text import Text

def run_with_spinner(fn, *args, **kwargs):
    """Run fn(*args, **kwargs) in background thread, show spinner on main thread."""
    result = []
    exc = []
    done = threading.Event()

    def worker():
        try:
            result.append(fn(*args, **kwargs))
        except Exception as e:
            exc.append(e)
        finally:
            done.set()

    threading.Thread(target=worker, daemon=True).start()
    spinners = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    with Live(console=console, refresh_per_second=10) as live:
        while not done.is_set():
            live.update(Text(f"{spinners[i % len(spinners)]}  Searching...", style="bold cyan"))
            done.wait(timeout=0.1)
            i += 1

    if exc:
        raise exc[0]
    return result[0] if result else None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93 (2023) | Must migrate; old approach emits deprecation warning |
| InquirerPy for arrow-key menus | questionary 2.1.1 | InquirerPy went inactive ~2022 | Direct replacement; questionary has cleaner API |
| `Rich.Prompt.ask()` for CLI input | `questionary.select()` | Phase 1 change | Rich prompts require typing; questionary is fully arrow-navigable |

**Deprecated/outdated in this codebase:**
- `@app.on_event("startup")` in `routes.py`: Deprecated since FastAPI 0.93. Replace with `lifespan` (FIX-02).
- `Rich.Prompt.ask()` / `Rich.Confirm.ask()` in `main.py`: These require typing. Replace with `questionary` equivalents for the new TUI layer.
- Typer `@app.command()` decorator pattern: Will be replaced by `questionary` menu loop as the primary interface. Typer can remain as a thin wrapper that calls `tui_main()`.

---

## Open Questions

1. **ZIP Discovery display in wizard**
   - What we know: The existing wizard shows a Rich table of discovered ZIPs and asks for exclusions (typed). D-08 says only city/ZIP entry requires typing.
   - What's unclear: How should ZIP exclusion work with arrow keys? The current UI shows up to 30 ZIPs in a table and asks for a typed comma-separated exclusion list.
   - Recommendation: Use `questionary.checkbox()` to display ZIPs discovered, with all pre-checked. User unchecks to exclude. This eliminates the exclusion typing entirely. Cap display at 30 ZIPs (pagination if more).

2. **Search summary panel before confirmation (D-12)**
   - What we know: D-12 requires a Rich panel showing all selected criteria before "Search now?" confirm.
   - What's unclear: Layout of the summary panel — flat list vs two-column grid.
   - Recommendation: Use Rich `Table` with two columns (Field | Value) inside a `Panel`. Skip fields where value is None/Any.

3. **"Saved Searches" menu item scope in Phase 1**
   - What we know: D-06 includes "Saved Searches" in the main menu. Phase 2 is where the full saved searches browser is built (CFG-06).
   - What's unclear: Should Phase 1 implement a basic "Saved Searches" view, or stub it?
   - Recommendation: Phase 1 should implement a basic read-only list with questionary.select for picking a saved search to run again. Full management (toggle active/delete) is Phase 2.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 (already in dev dependencies) |
| Config file | None detected — pyproject.toml has no `[tool.pytest.ini_options]` section |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIX-02 | lifespan migration — no DeprecationWarning on FastAPI import | unit | `pytest tests/test_api_lifespan.py -x` | ❌ Wave 0 |
| CLI-01 | splash art renders without UnicodeError on narrow terminal | unit | `pytest tests/test_tui_splash.py -x` | ❌ Wave 0 |
| CLI-03 | menu loop returns expected choice string from questionary | unit | `pytest tests/test_tui_menu.py -x` | ❌ Wave 0 |
| CLI-04/05 | wizard maps option labels to correct SearchCriteria fields | unit | `pytest tests/test_tui_wizard.py -x` | ❌ Wave 0 |
| CLI-06/07 | background search thread completes and sets done_event | unit | `pytest tests/test_tui_search.py -x` | ❌ Wave 0 |
| CLI-08 | results table renders without error for 0, 1, 50 listings | unit | `pytest tests/test_tui_results.py -x` | ❌ Wave 0 |
| CLI-09 | menu loop returns to menu after action completes | unit | `pytest tests/test_tui_menu.py::test_returns_to_menu -x` | ❌ Wave 0 |

Note: questionary prompts are non-trivially testable in isolation (they require interactive terminal input). Tests should mock `questionary.select().ask()` return values using `unittest.mock.patch`.

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — package marker
- [ ] `tests/conftest.py` — shared fixtures including mock console, mock questionary
- [ ] `tests/test_api_lifespan.py` — covers FIX-02
- [ ] `tests/test_tui_splash.py` — covers CLI-01, CLI-02
- [ ] `tests/test_tui_menu.py` — covers CLI-03, CLI-09
- [ ] `tests/test_tui_wizard.py` — covers CLI-04, CLI-05
- [ ] `tests/test_tui_search.py` — covers CLI-06, CLI-07
- [ ] `tests/test_tui_results.py` — covers CLI-08
- [ ] `pyproject.toml` update: add `[tool.pytest.ini_options]` with `testpaths = ["tests"]`

---

## Sources

### Primary (HIGH confidence)
- questionary PyPI: https://pypi.org/project/questionary/ — v2.1.1, Aug 28 2025, confirmed active
- questionary docs: https://questionary.readthedocs.io/en/stable/ — prompt types, Style API
- art PyPI: https://pypi.org/project/art/ — v6.5, Apr 12 2025
- Rich Live docs: https://rich.readthedocs.io/en/latest/live.html — Live context, thread safety
- Rich Table docs: https://rich.readthedocs.io/en/latest/tables.html — column styles
- FastAPI lifespan docs: https://fastapi.tiangolo.com/advanced/events/ — lifespan migration pattern
- Python threading docs: https://docs.python.org/3/library/threading.html — Thread, Event

### Secondary (MEDIUM confidence)
- Rich Issue #1530 — Live thread safety: https://github.com/Textualize/rich/issues/1530
- Uvicorn daemon thread pattern: https://bugfactory.io/articles/starting-and-stopping-uvicorn-in-the-background/
- InquirerPy Snyk inactive: https://snyk.io/advisor/python/inquirerpy — Inactive classification

### Tertiary (LOW confidence)
- questionary + Typer co-architecture: https://dev.to/e4c5nf3d6/dynamic-nested-menus-in-a-python-cli-3g9p — community source, unverified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — questionary 2.1.1 and art 6.5 confirmed on PyPI with recent release dates; Rich already installed
- Architecture patterns: HIGH — FIX-02 from official FastAPI docs; threading pattern from Python stdlib docs; questionary API from official docs
- Pitfalls: HIGH for Rich/questionary conflict (documented in prior research from Rich issue tracker), HIGH for threading/blocking search (documented in PITFALLS.md from codebase analysis)
- Test map: MEDIUM — test structure is standard pytest; questionary mocking approach is common but specific mock paths need confirmation during Wave 0

**Research date:** 2026-03-25
**Valid until:** 2026-06-25 (questionary and art are stable; Rich API stable; FastAPI lifespan API stable)
