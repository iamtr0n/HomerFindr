# Roadmap: HomerFindr

## Overview

HomerFindr ships as a polished dual-interface home search tool. The working-but-utilitarian Python/FastAPI + React codebase gets transformed into a delightful experience: a zero-typing, arrow-key CLI with ASCII art and Rich visuals, a Zillow/Redfin-inspired web dashboard with proper property cards, and a globally-installable desktop command. The four phases build sequentially — interactive CLI core first, then settings/configuration on top of that menu structure, then web UI redesign in parallel, and finally bridging both interfaces with desktop packaging.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Interactive CLI Core** - Arrow-key navigation, ASCII art splash, search wizard, and Rich results — the zero-typing CLI experience
- [ ] **Phase 2: CLI Settings and Configuration** - Settings page, SMTP wizard, saved searches browser, first-run setup, and persistent config
- [ ] **Phase 3: Web UI Redesign** - Professional Zillow/Redfin-inspired dashboard with property cards, sortable results, and cross-cutting data quality fixes
- [ ] **Phase 4: Bridge and Desktop Packaging** - Launch Web UI from CLI, global homerfindr command, and macOS .app shortcut

## Phase Details

### Phase 1: Interactive CLI Core
**Goal**: Users can run homerfindr and navigate entirely with arrow keys — no typing required for any search
**Depends on**: Nothing (first phase)
**Requirements**: FIX-02, CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, CLI-08, CLI-09
**Success Criteria** (what must be TRUE):
  1. Running `python main.py` (or `homerfindr`) shows a colorful ASCII art house splash screen before the main menu
  2. The main menu is navigable with arrow keys and Enter — no text input needed to reach any option
  3. A complete home search (all 15 fields) can be configured and submitted using only arrow keys and Enter
  4. A Rich progress spinner is visible during the search scrape and the CLI stays interactive (does not freeze)
  5. Search results appear in a colorful Rich table with price, beds, baths, sqft, and address; pressing Enter or a key returns to main menu
**Plans:** 4/4 plans executed

Plans:
- [x] 01-01-PLAN.md — Fix FastAPI deprecation (FIX-02), add questionary/art deps, create TUI package with shared styles
- [x] 01-02-PLAN.md — ASCII art splash screen with typewriter animation, main menu loop, entry point rewiring
- [x] 01-03-PLAN.md — 15-field search wizard with arrow-key navigation and pre-built option lists
- [x] 01-04-PLAN.md — Non-blocking search with spinner, colorful results table, URL opening, save flow

### Phase 2: CLI Settings and Configuration
**Goal**: Users can configure email reports, set search defaults, and manage saved searches without leaving the CLI
**Depends on**: Phase 1
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06, CFG-07
**Success Criteria** (what must be TRUE):
  1. First launch triggers a guided setup wizard where users can set location defaults and optionally configure SMTP — all with arrow keys
  2. The Settings menu lets a user add/remove email recipients and set a default search location without typing in a free-form prompt
  3. The SMTP wizard walks through server, port, email, and password fields with a test-send step, and saves credentials to `~/.homerfindr/config.json`
  4. Saved searches are browsable from the main menu — user can view, run, toggle active/inactive, and delete via arrow-key list
**Plans:** 1/3 plans executed

Plans:
- [x] 02-01-PLAN.md — Config module (load/save JSON), SMTP wizard with provider presets and test-send, first-run setup wizard
- [x] 02-02-PLAN.md — Settings page (Email/Defaults/About sub-pages), saved searches browser (table + Run Now/Toggle/Rename/Delete)
- [ ] 02-03-PLAN.md — Wire all Phase 2 modules into menu.py, end-to-end verification checkpoint

### Phase 3: Web UI Redesign
**Goal**: The web dashboard looks and feels like a professional real estate app — clean property cards, sortable results, and accurate data
**Depends on**: Nothing (independent of CLI phases, can proceed after Phase 1 is underway)
**Requirements**: FIX-01, FIX-03, FIX-04, WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06, XC-01, XC-02, XC-03
**Success Criteria** (what must be TRUE):
  1. Searching from the web UI returns results (no 404 on the preview endpoint) and the result count in the header is accurate
  2. Each property is displayed as a card with a thumbnail photo, price, beds/baths/sqft, and a working click-through link to the original listing
  3. Results can be sorted (price, sqft, beds) and filtered (price range, min beds, min baths) from the dashboard
  4. The dashboard home page shows saved searches and recent results; the design uses a clean real estate color scheme with professional typography
  5. When a provider returns an error or 403, a visible error message tells the user which provider failed rather than silently returning empty results
**Plans:** 3/4 plans executed

Plans:
- [x] 03-01-PLAN.md — Fix bugs (FIX-01, FIX-03, FIX-04), provider error collection (XC-02 backend), enhanced dedup (XC-01)
- [x] 03-02-PLAN.md — Design system foundation: Tailwind brand palette, shadcn/ui primitives (Card/Badge/Button), HomerFindr branding (XC-03)
- [ ] 03-03-PLAN.md — Redesign PropertyCard and Dashboard with shadcn/ui, stat header, recent activity section (WEB-01, WEB-02, WEB-03, WEB-05)
- [x] 03-04-PLAN.md — Client-side filter controls for SearchResults (WEB-04), provider error banners on both search pages (XC-02 frontend, WEB-05)

### Phase 4: Bridge and Desktop Packaging
**Goal**: HomerFindr feels like a real desktop application — launchable from anywhere, with CLI and web UI connected as one tool
**Depends on**: Phase 1 (CLI menu hook), Phase 3 (polished web UI worth launching)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05
**Success Criteria** (what must be TRUE):
  1. Typing `homerfindr` in any terminal window launches the interactive CLI (installed globally via pipx)
  2. Selecting "Launch Web UI" from the CLI main menu starts the FastAPI server and opens the browser automatically — no manual server start needed
  3. Closing the CLI (or selecting Exit) shuts down the background FastAPI server gracefully with no zombie processes
  4. A macOS .app bundle in the Dock opens a terminal running homerfindr when double-clicked
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

Note: Phase 3 is independent of Phase 2 and can be worked in parallel with Phases 1-2 by a second developer (or Claude in a separate context). Phase 4 requires both Phase 1 and Phase 3 to be complete.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Interactive CLI Core | 4/4 | Complete |  |
| 2. CLI Settings and Configuration | 1/3 | In Progress|  |
| 3. Web UI Redesign | 3/4 | In Progress|  |
| 4. Bridge and Desktop Packaging | 0/TBD | Not started | - |
