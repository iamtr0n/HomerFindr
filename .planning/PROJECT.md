# HomerFindr

## What This Is

A polished home search aggregator that pulls listings from multiple platforms (Realtor.com, Redfin, and more) into one place. It ships as a real desktop application: a zero-typing, arrow-key CLI with ASCII art and Rich visuals, plus a Zillow/Redfin-inspired web dashboard — all launchable from a single global `homerfindr` command. Built for personal use and sharing with friends/family who are house hunting.

## Core Value

Find homes fast across all platforms without juggling multiple websites — zero typing required in the CLI, just arrows and Enter.

## Current State

**Shipped: v1.0 MVP** (2026-03-26) — 4 phases, 13 plans, ~4,800 LOC (Python + React)

- ✅ Arrow-key CLI with ASCII art splash, 15-field search wizard, Rich results table
- ✅ Settings UI, SMTP wizard, first-run setup, saved searches browser
- ✅ Zillow/Redfin-inspired web dashboard with shadcn/ui design system
- ✅ `pipx install .` → `homerfindr` global command; "Launch Web UI" opens browser from CLI
- ✅ macOS double-click `.command` launcher and Platypus Dock wrapper

**Known gaps for v1.1:**
- Phase 2 Plan 3 (menu.py wiring for Settings/Saved Searches) needs verification
- Property card thumbnails not yet fetching real listing photos
- CLI color/animation polish (progress bars, animated loading) partially complete

## Requirements

### Validated

- ✓ Multi-platform search (Realtor.com via homeharvest, Redfin) — existing
- ✓ Search criteria model (price, beds, baths, sqft, lot, year, floors, basement, garage, HOA) — existing
- ✓ Radius-based search with ZIP code discovery — existing
- ✓ Saved searches with SQLite persistence — existing
- ✓ FastAPI backend with REST endpoints — existing
- ✓ React frontend with property cards and search form — existing
- ✓ CLI with Typer — existing
- ✓ Email reports via SMTP — existing
- ✓ Provider architecture (pluggable BaseProvider) — existing
- ✓ Arrow-key interactive CLI — all navigation via arrows + Enter, zero typing — v1.0
- ✓ ASCII art house-themed splash/loading screen — colorful, fun, impressive — v1.0
- ✓ Main menu system — Search, Saved Searches, Settings, Launch Web UI, Exit — v1.0
- ✓ Settings/Options page in CLI — configure SMTP, email recipients, search defaults — v1.0
- ✓ SMTP setup wizard in CLI — guided arrow-key flow to configure email — v1.0
- ✓ First-run experience — guided setup on first launch — v1.0
- ✓ Desktop launchable — global `homerfindr` CLI command + macOS launcher — v1.0
- ✓ Professional web dashboard — shadcn/ui design system, stat header, saved search cards — v1.0
- ✓ Property cards — source badge, price, beds/baths/sqft, click-through links — v1.0
- ✓ Sortable/filterable search results — client-side price/beds/baths filters — v1.0
- ✓ Provider error banners — visible when Realtor.com or Redfin returns 403/error — v1.0

### Active (v1.1 candidates)

- [ ] Property card thumbnail photos — fetch real listing images
- [ ] Phase 2 settings/saved-searches wiring — full verification of menu integration
- [ ] CLI animation polish — progress bars, richer loading states

### Out of Scope

- User accounts / authentication — personal tool, not a SaaS
- Deployment to cloud hosting — runs locally, web UI served from local machine
- Zillow API integration — requires paid RapidAPI subscription, defer to future
- Mobile app — web dashboard is responsive enough
- Real-time notifications / push alerts — email reports cover this

## Context

**Shipped v1.0.** Tech stack: Python 3.11+, FastAPI, SQLite, questionary + Rich (TUI), React 18, Tailwind CSS + shadcn/ui primitives, Vite. The codebase is ~4,800 LOC across Python and React. All four v1.0 phases are complete and verified.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep Python/FastAPI backend | Working, solid architecture, no reason to change | ✓ Good — zero issues |
| questionary for arrow-key menus | Rich already in stack, questionary pairs cleanly | ✓ Good — smooth wizard UX |
| Zillow/Redfin-inspired web UI | User wants professional real estate look | ✓ Good — shadcn/ui delivered it |
| Local-only deployment | Target audience is personal + friends/family | ✓ Good — still correct |
| uvicorn.Server + daemon thread | Background server without subprocess complexity | ✓ Good — clean lifecycle |
| .command file over Platypus (primary) | Zero dependencies, works out of the box on macOS | ✓ Good — Platypus as optional polish |
| shadcn/ui owned components | Copied to project, fully customizable | ✓ Good — no registry lock-in |

## Constraints

- **Stack**: Keep existing Python + React stack — no rewrites
- **Data sources**: Only free providers (homeharvest, redfin packages) — no paid APIs
- **Local-first**: Everything runs on the user's machine, no cloud dependencies
- **Zero typing**: Search wizard must be navigable entirely with arrows + Enter

---
*Last updated: 2026-03-26 after v1.0 milestone*
