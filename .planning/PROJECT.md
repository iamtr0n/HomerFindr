# HomerFindr

## What This Is

A polished home search aggregator that pulls listings from multiple platforms (Realtor.com, Redfin, and more) into one place. It has two equally important interfaces: a fun, colorful CLI with arrow-key navigation and ASCII art, and a clean Zillow/Redfin-inspired web dashboard. Built for personal use and sharing with friends/family who are house hunting.

## Core Value

Find homes fast across all platforms without juggling multiple websites — zero typing required in the CLI, just arrows and Enter.

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

### Active

- [ ] Arrow-key interactive CLI — all navigation via arrows + Enter, zero typing for searches
- [ ] ASCII art house-themed splash/loading screen — colorful, fun, impressive
- [ ] Main menu system — Search, Saved Searches, Settings, Launch Web UI, Exit
- [ ] Settings/Options page in CLI — configure SMTP, email recipients, search defaults
- [ ] SMTP setup wizard in CLI — guided arrow-key flow to configure email
- [ ] Desktop launchable — global `homerfindr` CLI command + macOS .app/dock shortcut
- [ ] Colorful/fun CLI experience — Rich-powered colors, progress bars, animated house loading
- [ ] Web UI redesign — clean, minimal, Zillow/Redfin-inspired professional dashboard
- [ ] Property cards with thumbnails, key details, click-through to original listing
- [ ] Web dashboard — saved searches overview, recent results, quick actions
- [ ] Search results display — sortable, filterable grid/list in both CLI and web
- [ ] Streamlined search flow — pre-built option lists for every field (no free typing)
- [ ] First-run experience — guided setup on first launch (location, preferences, optional SMTP)

### Out of Scope

- User accounts / authentication — personal tool, not a SaaS
- Deployment to cloud hosting — runs locally, web UI served from local machine
- Zillow API integration — requires paid RapidAPI subscription, defer to future
- Mobile app — web dashboard is responsive enough
- Real-time notifications / push alerts — email reports cover this

## Context

The existing codebase is a working Python/FastAPI app with a React/Vite frontend. The CLI exists but uses basic Typer prompts that require typing. The frontend works but has generic/plain styling. The core search logic and provider architecture are solid. The main work is UX polish: making the CLI delightful with arrow-key navigation and ASCII art, making the web UI look professional, and packaging it all for easy desktop launch.

**Tech stack (keeping):** Python 3.11+, FastAPI, SQLite, Typer, Rich, React, Tailwind CSS, Vite
**Adding:** inquirerpy or simple-term-menu (arrow-key menus), pyfiglet/art (ASCII), macOS .app wrapper

## Constraints

- **Stack**: Keep existing Python + React stack — no rewrites
- **Data sources**: Only free providers (homeharvest, redfin packages) — no paid APIs
- **Local-first**: Everything runs on the user's machine, no cloud dependencies
- **Zero typing**: Search wizard must be navigable entirely with arrows + Enter

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep Python/FastAPI backend | Working, solid architecture, no reason to change | — Pending |
| Arrow-key CLI with Rich | Rich already in stack, pairs well with inquirerpy for interactive menus | — Pending |
| Zillow/Redfin-inspired web UI | User wants professional real estate look, not playful | — Pending |
| Local-only deployment | Target audience is personal + friends/family, not public | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-25 after initialization*
