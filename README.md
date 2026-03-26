# HomerFindr 🏠

Search every home listing. Find the one.

HomerFindr pulls listings from **Realtor.com** and **Redfin** into a single polished terminal UI — no browser juggling, no typing, just arrows and Enter.

## Install

```bash
pip install homesearch
```

Or clone and install locally:

```bash
git clone https://github.com/iamtr0n/HomerFindr.git
cd HomerFindr
pip install -e .
```

## Usage

```bash
homerfindr        # launch the interactive TUI
homerfindr serve  # launch the web dashboard
```

## Features

- Arrow-key search wizard with 19 configurable filters
- Live ZIP progress bar with running found count during search
- Multi-area mode — combine ZIP codes from multiple cities, each with its own radius
- No-results diagnostics — color-coded per-filter breakdown with specific fix recommendations
- Targeted edit — change any single filter at the summary screen without restarting
- Match scoring & gold star badges for perfect matches
- Highway proximity detection
- Saved searches with run history
- Web dashboard (FastAPI + React)
- Auto-update notifications

---

## Changelog

### v1.2.0 — 2026-03-26

**New features**
- **Cool ASCII splash** — block-art HOMER/FINDR logo with typewriter reveal and compact mode for narrow terminals
- **Version badge** — version shown in splash and available as `homesearch.__version__`
- **Auto-update check** — background thread checks GitHub on every launch; shows update banner with install command
- **ZIP codes visible in search summary** — shows actual ZIP codes (up to 10, "+N more") instead of just a count
- **No-results diagnostics: color-coded + recommendations**
  - #1 culprit shown in bold red with data-driven fix (e.g. "Try raising price max to $512,000")
  - Other filters shown in yellow with dimmed hints
  - Hint points to "Edit a filter" for quick adjustment
- **Targeted filter editing** — "Edit a filter..." at summary lets you change any of the 19 wizard steps in place
- **Per-location radius** — multi-area mode asks for radius per city
- **Duplicate location guard** — silently skips duplicate cities in multi-area mode
- **Back navigation on every step** — `← Back` embedded in every wizard screen

**Bug fixes**
- Fixed `has_fireplace`, `has_pool`, `has_ac` filters using `is not True` instead of `is False` — was filtering out listings where the field was simply unknown/unset, causing zero results when any of these were required
- Fixed `coming_soon` listing type mapping to homeharvest's `pending` value

---

### v1.1.0 — 2026-03-20

- Live "found so far" counter during ZIP search spinner
- Pre-filter raw listing capture for diagnostics
- Multi-provider deduplication by normalized address
- Match scoring with badges (garage, basement, pool, HOA, beds/baths, price, new build)
- Gold star listings for perfect matches
- Highway proximity enrichment (optional)
- Saved search browser with run/rename/delete/toggle
- House style filter with descriptions
- School rating filter
- HOA max filter

---

### v1.0.0 — 2026-03-01

- Initial release
- Realtor.com + Redfin providers
- Interactive TUI wizard
- ZIP code discovery by radius
- FastAPI web dashboard
- SQLite persistence
- Daily email reports via APScheduler

---

## Update

```bash
pip install --upgrade homesearch
```

HomerFindr checks for updates automatically on every launch and will notify you when a new version is available.
