# Project Research Summary

**Project:** HomerFindr — UX Polish Milestone
**Domain:** Home search aggregator — dual-interface (CLI + web dashboard)
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

HomerFindr is a local-first, personal-use home search aggregator that scrapes Realtor.com and Redfin and presents results through both an interactive CLI and a React web dashboard. The UX polish milestone transforms an already-working but utilitarian tool into a polished, delightful experience: arrow-key navigation throughout the CLI, an ASCII art splash screen, a professional property card web UI, and a global desktop command. The recommended approach keeps all changes strictly at the surface layer — the existing FastAPI / service / provider architecture is correct and should not be touched. New libraries (questionary for interactive menus, art for ASCII art, shadcn/ui components for the web) layer cleanly on top of what exists.

The single most important recommendation is to fix two known bugs before building anything new: the double `/api` prefix that returns 404 on every preview search, and the `@app.on_event("startup")` deprecation that leaks warnings into the CLI output. Building a polished UI on top of broken plumbing wastes time. After those fixes, the work naturally splits into two independent tracks — CLI interactive layer and web UI redesign — that can be developed in parallel, joined in a final phase that bridges them with the "Launch Web UI from CLI" feature and desktop packaging.

The primary risks are: (1) Rich and questionary/InquirerPy output corruption if the two are ever run concurrently rather than sequentially — this is an easy mistake with a visually obvious failure mode; (2) blocking HTTP scraping freezing the interactive spinner — requires running the search in a background thread; (3) macOS .app packaging being significantly more complex than it appears — ship the global `homerfindr` CLI command via pipx first and treat the .app as optional. All three risks have clear, validated mitigations and should not block delivery if addressed in the correct order.

---

## Key Findings

### Recommended Stack

The existing Python 3.11 / FastAPI / React / Vite / Tailwind stack requires only four additions for this milestone. On the Python side: **questionary 2.1.1** for arrow-key interactive menus (InquirerPy is abandoned/inactive per Snyk; simple-term-menu is Linux-primary) and **art 6.5** for the ASCII art splash screen (677+ fonts, simpler API than pyfiglet). On the frontend: **shadcn/ui** CLI-installed component primitives (not a library — components are owned code, zero runtime dependency, Tailwind-compatible). For packaging: **pipx** for global CLI installation with **Platypus** (free, v5.5.0, Dec 2025) as the macOS .app wrapper — far simpler than PyInstaller for a CLI-first tool since it just wraps the installed shell command rather than bundling the Python runtime.

Note: ARCHITECTURE.md diverges slightly from STACK.md on the interactive menu library — ARCHITECTURE.md uses InquirerPy throughout while STACK.md recommends questionary. **Resolution: use questionary**, which is confirmed actively maintained. The underlying technology is the same (both use prompt_toolkit); questionary has the cleaner API for pre-built option lists.

**Core technologies:**
- **questionary 2.1.1**: Arrow-key select/checkbox/confirm prompts — actively maintained (Aug 2025), prompt_toolkit-based, no conflict with Rich
- **art 6.5**: ASCII art splash screen — 677+ fonts, MIT, one-call API, works alongside Rich
- **shadcn/ui (latest)**: React component primitives — copy-paste into codebase, no runtime dependency, Tailwind v3 compatible
- **pipx**: Global CLI installation — handles Python upgrades gracefully, recommended over `pip install -e .`
- **Platypus 5.5.0**: macOS .app wrapper — wraps installed shell command, no Python bundling needed

### Expected Features

**Must have (table stakes — CLI):**
- Arrow-key navigation throughout with visual focus indicator and back/exit at every screen
- Rich progress spinner during search (blocking HTTP takes 175+ seconds for large searches)
- Scrollable, sorted results table in Rich
- Contextual help overlay (? key pattern from lazygit)
- Saved searches accessible from main menu
- First-run setup wizard with SMTP configuration

**Must have (table stakes — web):**
- Property cards with photo thumbnail, price, beds/baths/sqft, click-through to listing
- Filter panel (price, beds, baths, sqft) and sort dropdown
- Loading skeleton states and empty state guidance
- Responsive layout
- Results count header ("X homes found")

**Should have (differentiators):**
- ASCII art splash screen with house theme — signals craft, memorable
- "Launch Web UI" from CLI main menu — bridges both interfaces
- Global `homerfindr` command — tools that require `cd ~/projects && python main.py` get abandoned
- HTML email reports (Jinja2 template upgrade from plain text)
- macOS .app / Dock shortcut via Platypus

**Defer:**
- Inline CLI result comparison — High complexity, limited MVP value
- Quick-action favorites from CLI — requires new DB table + sync endpoint
- Client-side favorites/starring
- Map-based search, user accounts, push notifications, cloud deployment (anti-features)

### Architecture Approach

The milestone adds three new surface components on top of the existing layered architecture without modifying the service layer. The Interactive TUI Shell (questionary + Rich + art, living in `homesearch/tui/` or extending `main.py`) drives all CLI interactions and delegates entirely to existing services. A thin Launcher module starts uvicorn in a daemon thread and opens the browser. The React frontend is a visual redesign in-place — no new API endpoints, no new state management, same Vite + TanStack Query stack. Desktop packaging is a configuration concern, not a code concern.

**Major components:**
1. **Interactive TUI Shell** — splash, main menu, search wizard, results display, settings/SMTP wizard; delegates to existing service layer
2. **FastAPI Launcher (daemon thread)** — starts uvicorn non-blocking via `uvicorn.Config` + `uvicorn.Server` in `threading.Thread(daemon=True)`; uses `server.started` flag polling before `webbrowser.open()`
3. **Redesigned React Web Frontend** — PropertyCard, Dashboard, sortable results grid, filter panel; works entirely with existing `/api/*` endpoints
4. **Desktop Launcher / Global Command** — `homerfindr` entry point in `pyproject.toml`, `pipx install .` for global use, optional Platypus `.app` for Dock

### Critical Pitfalls

1. **Rich + questionary output corruption** — never run Rich's Live/Progress context concurrently with a questionary/InquirerPy prompt; keep interaction strictly sequential (prompt returns value, then Rich renders). Construct one `Console` instance at startup and pass it everywhere.

2. **Blocking HTTP scraping freezes the interactive spinner** — wrap search calls in `threading.Thread`; show Rich Live spinner on main thread; provide explicit "press Q to cancel" escape; cap ZIP batch size with user warning.

3. **Double `/api` prefix 404 bug** — fix `@app.post("/api/search/preview")` route prefix before any web UI work. Verify with a smoke test (does Search return results?) before writing any frontend code.

4. **FastAPI deprecation warnings corrupt Rich output** — fix `@app.on_event("startup")` → `lifespan` context manager before building the CLI launcher; redirect uvicorn subprocess stdout/stderr away from the terminal.

5. **macOS .app Gatekeeper failures and Homebrew Python breakage** — ship the global `homerfindr` CLI command via `pipx` first; treat `.app` as optional and use Platypus (shell wrapper) rather than PyInstaller (full Python bundle). Never use `pip install -e .` into system/Homebrew Python for global commands.

---

## Implications for Roadmap

Based on combined research, the work falls into four natural phases. Phases 1 and 3 are largely independent and could be parallelized with two developers; Phase 2 depends on Phase 1's menu structure; Phase 4 depends on both Phase 1 (menu hook) and Phase 3 (polished web UI worth launching).

### Phase 1: Interactive CLI Core

**Rationale:** The arrow-key navigation is the foundation of the entire CLI experience. All other CLI features (SMTP wizard, saved searches, "Launch Web UI" trigger) hang off the main menu structure built here. Fix both blocking bugs (double `/api` prefix is web-only, but the FastAPI startup deprecation affects CLI launch) in this phase to avoid corruption later.
**Delivers:** Fully interactive CLI with splash screen, arrow-key main menu, search wizard, Rich results table, progress spinner, back/exit at every screen.
**Addresses:** All CLI table stakes features — arrow-key navigation, progress feedback, scrollable results, visual focus indicators.
**Avoids:** Pitfall 1 (Rich + questionary conflict), Pitfall 2 (blocking HTTP), Pitfall 11 (deprecation warnings in CLI output).
**Stack used:** questionary 2.1.1, art 6.5, Rich (existing).

### Phase 2: CLI Settings, SMTP Wizard, and Saved Searches

**Rationale:** Depends on Phase 1's menu structure being in place. First-run setup wizard (SMTP config) is table stakes — email reports silently fail without it. Saved searches browser in CLI completes the core loop.
**Delivers:** First-run experience that configures SMTP on first launch, settings page with arrow-key SMTP flow, saved searches list/run/delete in CLI.
**Addresses:** First-run setup wizard, saved searches accessible from main menu, persistent filter state.
**Avoids:** Pitfall 10 (SMTP wizard credential overwrite — use `python-dotenv` `set_key()`), Pitfall 13 (zero-typing constraint for location — use questionary FuzzyPrompt).
**Stack used:** questionary (existing from Phase 1), python-dotenv (existing).

### Phase 3: Web UI Redesign

**Rationale:** Independent of CLI phases. Can be built in parallel with Phases 1-2. The double `/api` prefix bug must be fixed as the first commit of this phase — no frontend work before that smoke test passes. Tailwind version must be pinned before any styling. `sortedResults` duplication must be extracted to a shared utility before touching both pages.
**Delivers:** Professional property card UI with thumbnails, sortable/filterable results grid, saved searches dashboard, loading/empty states, responsive layout.
**Addresses:** All web table stakes — property cards with photos, filter panel, sort dropdown, loading states, empty states, results count, responsive layout.
**Avoids:** Pitfall 4 (double `/api` prefix — fix first), Pitfall 8 (Tailwind version pin — check day one), Pitfall 9 (sortedResults duplication — extract before redesign), Pitfall 12 (`result_count` always 0 — remove/fix before building count UI), Pitfall 14 (dedup inconsistency — service-layer dedup before showing counts).
**Stack used:** shadcn/ui components (new), Tailwind 3.4.x (existing, pinned), React 18 / TanStack Query (existing).

### Phase 4: Bridge, Global Command, and Desktop Packaging

**Rationale:** Requires Phase 1 CLI menu to hook into and Phase 3 web UI worth launching. This phase connects both interfaces and makes the tool feel like a real desktop application.
**Delivers:** "Launch Web UI" item in CLI main menu that starts FastAPI in a daemon thread and opens the browser; `homerfindr` global command via pipx; optional Platypus macOS .app for Dock.
**Addresses:** Global CLI command (table stakes), "Launch Web UI" from CLI (differentiator), macOS .app / Dock shortcut (differentiator).
**Avoids:** Pitfall 3 (Gatekeeper failures — use Platypus, not PyInstaller; ship pipx first), Pitfall 7 (Homebrew Python breakage — use pipx), Pitfall 15 (APScheduler zombie thread — register `stop_scheduler` in lifespan), Anti-Pattern 2 (blocking uvicorn in main thread — daemon thread only).
**Stack used:** PyInstaller 6.19.0 (dev dependency, if needed), Platypus (external tool), pipx (user installs).

### Phase Ordering Rationale

- Phase 1 must come before Phase 2 because the settings and saved-searches screens are sub-menus of the main menu built in Phase 1.
- Phase 3 is independent but benefits from being slightly later so the double-API bug fix and Tailwind pin happen before CSS work begins.
- Phase 4 must come last because it bridges CLI (Phase 1) and web UI (Phase 3) and the bridge is only valuable once both are polished.
- The two known bugs (double `/api` prefix, FastAPI startup deprecation) should be addressed as pre-flight fixes before Phases 1 and 3 respectively, not their own phase.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (macOS .app via Platypus):** Platypus wrapping a pipx-installed command has edge cases around PATH availability in the app-launched Terminal session. Needs validation on a clean machine before declaring complete.
- **Phase 2 (SMTP validation):** Testing SMTP credentials in the wizard requires a live SMTP server or mock. May need a test-connection utility; research the python-dotenv + smtplib pattern for the wizard.

Phases with standard patterns (skip research-phase):
- **Phase 1:** questionary + Rich sequential pattern is well-documented; art library has a one-call API. Standard patterns throughout.
- **Phase 3:** shadcn/ui has an official Vite install guide; PropertyCard layout is a standard pattern. No research needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library choices verified against current PyPI releases and official docs; only PyInstaller .app terminal behavior rated MEDIUM |
| Features | HIGH | Web-verified against Zillow/Redfin/Realtor.com UX patterns and multiple real estate app analyses |
| Architecture | HIGH | Existing codebase is clean and well-isolated; new components have clear boundaries; uvicorn daemon thread pattern is MEDIUM confidence (community-verified, not official docs) |
| Pitfalls | HIGH | Majority sourced from internal CONCERNS.md (first-party) and official library docs; Gatekeeper/notarization specifics are MEDIUM |

**Overall confidence:** HIGH

### Gaps to Address

- **questionary vs InquirerPy discrepancy between research files:** STACK.md recommends questionary; ARCHITECTURE.md uses InquirerPy throughout. Both use prompt_toolkit under the hood. Resolution is questionary (actively maintained), but the architecture patterns in ARCHITECTURE.md are fully applicable — just substitute `questionary.select()` for `InquirerPy list prompts`.

- **PyInstaller .app terminal behavior on macOS 15 + Python 3.11:** The STACK.md caveat is real — PyInstaller `--windowed` suppresses stdout for CLI tools. Platypus avoids this entirely. Validate the Platypus approach on a clean machine early in Phase 4 before investing time in PyInstaller .app work.

- **Deduplication correctness:** CONCERNS.md documents that address-based deduplication is fragile. This needs to be fixed at the service layer before building result count displays in Phase 3. If dedup is complex, it may warrant its own sub-task or brief research spike.

- **APScheduler + lifespan migration:** Two independent bugs (missing `stop_scheduler` shutdown hook and deprecated `@app.on_event`) that need fixing before Phase 4's launcher integration. Small but must not be skipped.

---

## Sources

### Primary (HIGH confidence)
- questionary PyPI / GitHub (tmbo/questionary) — v2.1.1, Aug 2025, Python 3.9-3.14 confirmed
- art PyPI — v6.5, Apr 2025, 677+ fonts, MIT license
- PyInstaller PyPI — v6.19.0, Feb 2026, Python 3.8-3.14 supported
- shadcn/ui Vite installation guide (ui.shadcn.com/docs/installation/vite) — official Vite setup
- Rich documentation (rich.readthedocs.io) — Live context, threading, progress, tables
- pipx documentation (pipx.pypa.io) — global Python CLI install best practice
- HomeHarvest PyPI / GitHub — 403 blocking behavior documented in README
- FastAPI CORS docs — wildcard origin confirmed
- Internal CONCERNS.md — first-party codebase analysis, existing bugs documented

### Secondary (MEDIUM confidence)
- Uvicorn daemon thread pattern (bugfactory.io) — community-verified, not in official uvicorn docs
- Platypus macOS app wrapper (sveinbjorn.org/platypus) — v5.5.0, Dec 2025
- PyInstaller Gatekeeper notarization (Apple Developer Forums) — notarized app failure patterns
- Tailwind v4 dark mode migration (tailwindlabs/tailwindcss GitHub discussion) — config format changes
- Redfin scraping anti-bot measures (ScrapeOps) — community source

### Tertiary (LOW confidence)
- InquirerPy GitHub Issues — prompt_toolkit interaction edge cases (browsed, not exhaustively read)
- Rich GitHub Issues #979, #1530, Discussion #1791 — concurrent Live + input behavior

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
