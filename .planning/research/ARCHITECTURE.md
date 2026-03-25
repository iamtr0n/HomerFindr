# Architecture Patterns

**Project:** HomerFindr — polished CLI + web UX milestone
**Researched:** 2026-03-25
**Dimension:** Interactive CLI layer, web redesign, and desktop packaging integrated into existing FastAPI + React architecture

---

## Existing Architecture Summary

The existing codebase is a clean layered monorepo:

```
Models → Config → Database
                      ↓
           Providers → SearchService → API Layer (FastAPI)
                                    → CLI Layer (Typer/main.py)
                                          ↓
                                   Frontend (React SPA served by FastAPI)
```

The key constraint: the service layer is already well-isolated. CLI and API share the same services without duplication. This is the right foundation — the UX milestone adds surface layers on top without touching it.

---

## Recommended Architecture for This Milestone

The milestone adds three new surface components on top of the existing layers:

```
┌─────────────────────────────────────────────────────────┐
│  SURFACE LAYER (new this milestone)                      │
│                                                          │
│  ┌──────────────────┐   ┌───────────────────────────┐   │
│  │  Interactive TUI  │   │  Redesigned React Web UI  │   │
│  │  (InquirerPy +   │   │  (Tailwind redesign,       │   │
│  │   Rich + pyfiglet)│   │   property cards,          │   │
│  │                  │   │   saved search dashboard)  │   │
│  └────────┬─────────┘   └─────────────┬─────────────┘   │
│           │ calls                      │ REST /api/*      │
│  ┌────────▼─────────────────────────┐ │                  │
│  │  Desktop Launcher Shim           │ │                  │
│  │  (pipx install + macOS .app)     │ │                  │
│  └────────┬─────────────────────────┘ │                  │
└───────────┼───────────────────────────┼──────────────────┘
            ↓                           ↓
┌─────────────────────────────────────────────────────────┐
│  EXISTING LAYERS (unchanged)                             │
│  main.py (Typer) → services/ → providers/ → database    │
│  api/routes.py (FastAPI) → same services                 │
│  frontend/dist/ (served by FastAPI StaticFiles)          │
└─────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### Component 1: Interactive TUI Shell

**What it is:** A new interactive layer living in `homesearch/tui/` (or extending `main.py`) that replaces the existing typed-input Typer prompts with full arrow-key navigation flows.

**Responsibility:**
- Render the splash/ASCII art screen on startup
- Present main menu (Search, Saved Searches, Settings, Launch Web UI, Exit)
- Drive the search wizard entirely with InquirerPy list/checkbox/confirm prompts — no free typing for search fields
- Show Rich-powered progress bars and animated spinners during search fan-out
- Display results in Rich tables with pagination
- Manage the Settings and SMTP setup wizard
- Trigger `serve` (spawn FastAPI) and open browser on "Launch Web UI" selection

**What it does NOT own:**
- Search logic — delegates to existing `search_service`
- Database reads/writes — delegates to existing `database.py`
- HTTP serving — delegates to existing `api/routes.py`

**Communicates with:**
- `search_service.py` (run searches)
- `database.py` (load/save saved searches)
- `config.py` (read/write SMTP settings)
- `api/routes.py` (launches it via `uvicorn.Server` in a background thread)

### Component 2: FastAPI Server Launch (from TUI)

**What it is:** A thin function in `main.py` or a new `homesearch/launcher.py` that starts uvicorn non-blocking from the TUI "Launch Web UI" menu item.

**Pattern (HIGH confidence):**
Use `uvicorn.Config` + `uvicorn.Server` with `threading.Thread(target=server.run, daemon=True)`. This avoids the `asyncio` event loop conflict that occurs when calling `uvicorn.run()` (blocking) from the main thread that is already running InquirerPy's `prompt_toolkit` event loop.

```python
import threading, uvicorn, webbrowser, time

def launch_web_ui(port: int = 8000):
    config = uvicorn.Config("homesearch.api.routes:app", host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # Poll until ready (server.started flag set by uvicorn internally)
    for _ in range(20):
        if server.started:
            break
        time.sleep(0.25)
    webbrowser.open(f"http://127.0.0.1:{port}")
```

**Critical note:** InquirerPy uses `prompt_toolkit` which has its own event loop. Uvicorn's `asyncio` loop must run in a daemon thread, not the main thread, to avoid `set_wakeup_fd only works in main thread` errors. The daemon thread approach is the verified workaround.

**Communicates with:**
- `api/routes.py` (the FastAPI app instance)
- OS (webbrowser.open)

### Component 3: Redesigned React Web Frontend

**What it is:** An in-place visual redesign of `frontend/` — same Vite + React + Tailwind + TanStack Query stack, no architectural change, only UI layer changes.

**Responsibility:**
- New component library: `PropertyCard` with thumbnail, price, beds/baths/sqft badges, click-through link
- Dashboard page: saved searches overview, recent results count, quick "run" buttons
- Search results page: sortable/filterable grid with skeleton loading states
- Zillow/Redfin-inspired design tokens in Tailwind config (neutral grays, green accents, clean card shadows)
- Responsive layout that works on laptop screens (mobile is secondary, not out of scope)

**What it does NOT own:**
- API contract — existing `/api/*` endpoints are sufficient; no new endpoints needed for the redesign itself
- State management — TanStack Query is already correct; keep it

**Communicates with:**
- FastAPI `/api/*` REST endpoints (unchanged)

### Component 4: Desktop Launcher / Global Command

**What it is:** A packaging configuration that makes `homerfindr` a globally accessible shell command and optionally a macOS .app dock shortcut, without rewriting any code.

**Two-tier approach:**

**Tier 1 — Global CLI command (recommended for development):**
`pip install -e .` (already works) or `pipx install .` (preferred for end-user distribution).
`pyproject.toml` already defines `homesearch = "homesearch.main:app"`. Rename the entry point to `homerfindr` or add it as an alias.

```toml
[project.scripts]
homerfindr = "homesearch.main:app"
homesearch = "homesearch.main:app"  # keep for backward compat
```

After `pipx install .`, the `homerfindr` command is globally available in PATH.

**Tier 2 — macOS .app dock shortcut (optional, post-global-command):**
Use **Platypus** (free, maintained, v5.5.0 released Dec 2025) to wrap the `homerfindr` shell script as a native macOS .app bundle. Platypus creates a native app that opens Terminal and runs the command — exactly the behavior needed for a colorful CLI experience. This is simpler and more appropriate than PyInstaller for a tool that intentionally lives in the terminal.

PyInstaller is viable but overkill here: it bundles the entire Python runtime (~50–80MB), and the resulting `.app` would open a Terminal anyway since the UX is CLI-first. Platypus wraps the installed CLI script directly.

**Communicates with:**
- OS shell (invokes `homerfindr` from PATH)
- `main.py` entry point

---

## Data Flow

### Flow 1: Arrow-Key Search Wizard (new)

```
User launches `homerfindr`
    → main.py:tui_main() renders pyfiglet splash via Rich console
    → InquirerPy list prompt: main menu
    → User selects "Search"
    → InquirerPy list/checkbox prompts: location, price range, beds, baths, etc.
      (ALL selections from pre-built option lists — no free typing)
    → Criteria assembled into SearchCriteria model
    → zip_service.discover_zip_codes() → list of ZIPs
    → Rich progress bar starts
    → search_service.run_search(criteria) fans out to providers
    → Rich progress bar completes
    → Rich Table renders results in terminal
    → InquirerPy list: "Save this search? / Run again / Back / Exit"
```

### Flow 2: Launch Web UI from CLI (new)

```
User in main menu selects "Launch Web UI"
    → launcher.launch_web_ui(port=8000) called
    → uvicorn.Config + uvicorn.Server created
    → daemon thread started with server.run()
    → poll server.started flag (max 5s)
    → webbrowser.open("http://127.0.0.1:8000")
    → CLI menu returns to foreground (user can still navigate CLI)
    → Browser shows redesigned React dashboard
```

### Flow 3: First-Run Setup Wizard (new)

```
main.py:tui_main() checks config.py settings:
    - If DB missing → db.init_db()
    - If SMTP not configured → launch SMTP setup wizard (InquirerPy guided prompts)
    - If no saved searches → suggest creating first search
    → Writes settings to .env / config file via config.py
    → Proceeds to main menu
```

### Flow 4: Web Search (unchanged, styling only)

```
Browser POST /api/searches (SearchRequest JSON)
    → api/routes.py → search_service.run_search()
    → returns SearchResponse with Listing[]
    → React renders redesigned PropertyCard components
    → TanStack Query caches and invalidates on mutation
```

---

## Suggested Build Order

Dependencies between components determine phase ordering:

**Phase 1 — Interactive TUI core** (no dependencies on new components)
- InquirerPy + Rich integration in `main.py`
- Splash screen (pyfiglet + Rich)
- Main menu skeleton
- Arrow-key search wizard (replaces existing `search_interactive()`)
- Results display with Rich Table
- Depends on: existing service layer only

**Phase 2 — Settings, first-run, and saved searches in TUI** (depends on Phase 1 menu structure)
- First-run experience / setup wizard
- Settings page (SMTP config, search defaults)
- Saved searches browser in CLI (list, run, delete)
- Depends on: Phase 1 navigation structure

**Phase 3 — Web UI redesign** (independent of Phase 1/2, can run in parallel or after)
- Tailwind design tokens and layout system
- PropertyCard component with thumbnails
- Dashboard page (saved searches overview)
- Search results grid (sortable, filterable)
- Depends on: existing API (no new endpoints required)

**Phase 4 — Launch Web UI from CLI + desktop packaging** (depends on Phase 1 for the menu hook, and Phase 3 for the web UI being worth launching)
- `launcher.py` with uvicorn daemon thread + webbrowser.open
- `homerfindr` entry point rename in pyproject.toml
- pipx install documentation
- macOS .app via Platypus (optional, can be deferred)
- Depends on: Phase 1 (menu entry point), Phase 3 (polished web UI)

---

## Key Architecture Decisions

### Decision: InquirerPy over Textual for the interactive layer

**Verdict:** Use InquirerPy (with Rich for display, pyfiglet for ASCII art). Do not use Textual.

**Rationale:** Textual is a full-screen TUI framework — it takes over the entire terminal and renders a widget tree. HomerFindr's interaction model is sequential prompts (menu → wizard → results), not a persistent multi-pane dashboard. InquirerPy fits this model perfectly: each prompt renders, collects input, and returns a value. Rich then takes over to display results. The two libraries are sequential, not concurrent, so the prompt_toolkit / Rich rendering conflict is avoided naturally — InquirerPy prompts complete before Rich tables render.

**Confidence:** HIGH — InquirerPy is built on prompt_toolkit, actively maintained (kazhala/InquirerPy on GitHub), supports Python 3.7+, cross-platform. Rich is the display layer used after prompts return.

### Decision: Uvicorn daemon thread for "Launch Web UI", not subprocess

**Verdict:** Use `uvicorn.Config` + `uvicorn.Server` in a `threading.Thread(daemon=True)`, not `subprocess.Popen`.

**Rationale:** A daemon thread is simpler to manage (no process lifecycle, no PID tracking), shares the same Python process (no import overhead), and dies automatically when the CLI exits. The subprocess approach would require port negotiation, process kill on CLI exit, and is harder to signal when the server is ready. The daemon thread approach is widely verified for this pattern.

**Caveat:** The thread must be a daemon thread. If run as a non-daemon thread, `Ctrl+C` in the CLI will not terminate the server. uvicorn.Server sets a `started` flag that can be polled to confirm readiness before opening the browser.

**Confidence:** MEDIUM — the pattern is verified in community discussions and the uvicorn issue tracker, but not in official uvicorn docs as a first-class API.

### Decision: Platypus over PyInstaller for macOS .app

**Verdict:** Use Platypus to wrap the installed `homerfindr` CLI command as a macOS .app. Use pipx for global CLI installation.

**Rationale:** PyInstaller bundles a full Python runtime. For a CLI-first tool that is already installed via pip/pipx, bundling is unnecessary overhead (50–80MB app vs a 1KB Platypus shell wrapper). Platypus wraps the existing PATH command, opens Terminal, and runs it — which is exactly the desired UX. Platypus 5.5.0 was released December 2025, actively maintained.

**Confidence:** MEDIUM — Platypus is well-established for this use case; the pipx global install pattern is HIGH confidence.

### Decision: Web frontend is a redesign, not a rebuild

**Verdict:** Keep Vite + React 18 + Tailwind + TanStack Query. No new framework, no new state management.

**Rationale:** The existing `/api/*` endpoints already return the correct data. The redesign is entirely in the React component and Tailwind styling layer. Introducing a new framework (Next.js, SvelteKit, etc.) would require a new build pipeline and possibly new API patterns. The existing stack handles the requirements cleanly.

**Confidence:** HIGH — confirmed by existing codebase analysis.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Running InquirerPy and Rich simultaneously in the same frame

**What goes wrong:** InquirerPy uses prompt_toolkit to take control of the terminal cursor for rendering its interactive prompt. Calling `console.print()` (Rich) while an InquirerPy prompt is active corrupts the terminal display — lines overlap, cursor position breaks.

**Prevention:** Keep the interaction sequential. InquirerPy prompts run to completion and return a value. Only then does Rich render tables or spinners. Never print with Rich inside an InquirerPy callback that is still in the prompt phase.

### Anti-Pattern 2: Blocking uvicorn in the main thread from within TUI

**What goes wrong:** `uvicorn.run()` is blocking. Calling it from the Typer command that is also running InquirerPy's prompt_toolkit event loop raises `set_wakeup_fd only works in main thread` on Python 3.10+ because asyncio tries to install a signal handler on the main thread, which is already owned by prompt_toolkit.

**Prevention:** Always launch uvicorn in a `threading.Thread(daemon=True)`. The `uvicorn.Server.run()` method is the correct target, not `uvicorn.run()`.

### Anti-Pattern 3: Free-text input fields in the search wizard

**What goes wrong:** The project explicitly requires zero typing in the CLI search flow. Any use of `inquirerpy.prompt({"type": "input", ...})` for search fields breaks this contract.

**Prevention:** Every search field must use list/checkbox/confirm prompts with pre-built option lists. Location (ZIP code) should allow fuzzy search with InquirerPy's `fuzzy` prompt type, not a raw text input.

### Anti-Pattern 4: New API endpoints for the web redesign

**What goes wrong:** Adding new API routes to support frontend redesign features (e.g., separate endpoints for "dashboard stats") couples the frontend milestone to the backend and risks scope creep.

**Prevention:** The web redesign should work entirely with existing `/api/*` endpoints. If new data shapes are needed, prefer deriving them client-side from existing responses (e.g., count saved searches in the frontend, not a new `/api/stats` endpoint).

---

## Scalability Considerations

This is a local-first personal tool. Scalability concerns are minimal. The architectural constraint is:

| Concern | Current state | Implication |
|---------|---------------|-------------|
| Single-user | No auth, `allow_origins=["*"]` | Fine for local use; do not expose to LAN without auth |
| SQLite contention | CLI and web can run simultaneously, both hitting SQLite | Low risk for personal use; SQLite handles single-writer fine at this scale |
| uvicorn daemon thread lifetime | Dies when CLI process exits | Correct behavior; user sees server shutdown when they exit the CLI |
| Port collision | Hardcoded port 8000 | Add auto-increment fallback (8001, 8002) in `launcher.py` if 8000 is taken |

---

## Sources

- InquirerPy GitHub: [kazhala/InquirerPy](https://github.com/kazhala/InquirerPy) — prompt types, prompt_toolkit architecture, maintenance status
- rich-pyfiglet on PyPI: [rich-pyfiglet](https://pypi.org/project/rich-pyfiglet/) — Rich + pyfiglet integration wrapper
- Uvicorn threading pattern: [bugfactory.io — Starting and Stopping uvicorn in the Background](https://bugfactory.io/articles/starting-and-stopping-uvicorn-in-the-background/) — MEDIUM confidence
- server-thread library: [banesullivan/server-thread](https://github.com/banesullivan/server-thread) — reference implementation for ASGI background thread
- Platypus macOS app wrapper: [sveinbjorn.org/platypus](https://sveinbjorn.org/platypus) — v5.5.0, Dec 2025
- pipx global install: [pipx.pypa.io](https://pipx.pypa.io/latest/installation/) — HIGH confidence, official docs
- Textual TUI framework: [textual.textualize.io](https://textual.textualize.io/) — considered and rejected for this use case
- InquirerPy + Typer co-architecture: [DEV Community — Dynamic Nested Menus in Python CLI](https://dev.to/e4c5nf3d6/dynamic-nested-menus-in-a-python-cli-3g9p) — MEDIUM confidence (community source)
