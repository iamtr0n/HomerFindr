---
phase: quick
plan: 260326-dio
subsystem: search-filters, zip-discovery, scheduling
tags: [filters, fireplace, ac, heat, pool, coming-soon, zip-parsing, alerts, scheduler]
dependency_graph:
  requires: []
  provides: [has_fireplace-filter, has_ac-filter, heat_type-filter, has_pool-filter, coming-soon-listing-type, bare-city-zip-lookup, realtime-alert-job]
  affects: [homesearch/models.py, homesearch/services/zip_service.py, homesearch/database.py, homesearch/providers/homeharvest_provider.py, homesearch/providers/redfin_provider.py, homesearch/tui/wizard.py, homesearch/services/search_service.py, homesearch/services/scheduler_service.py]
tech_stack:
  added: []
  patterns: [description-keyword-detection, alter-table-migration, interval-scheduler-job, osascript-notifications]
key_files:
  created: []
  modified:
    - homesearch/models.py
    - homesearch/services/zip_service.py
    - homesearch/database.py
    - homesearch/providers/homeharvest_provider.py
    - homesearch/providers/redfin_provider.py
    - homesearch/tui/wizard.py
    - homesearch/services/search_service.py
    - homesearch/services/scheduler_service.py
decisions:
  - "Fireplace/pool filters use 'not True' check (None = unknown passes), preserving all listings with insufficient data"
  - "ZIP parser tries 2-word state names before 1-word to correctly handle 'New York', 'West Virginia', etc."
  - "DB migration uses ALTER TABLE in try/except to be idempotent on existing databases"
  - "Alert job uses listing.id (set after upsert) not source_id to compare against previous_ids set"
  - "heat_type filter skips listings with unknown heat_type (None) rather than excluding them"
metrics:
  duration_minutes: 15
  completed_at: "2026-03-26"
  tasks_completed: 3
  files_modified: 8
---

# Quick Task 260326-dio Summary

**One-liner:** Four new amenity filters (fireplace/AC/heat/pool) with description-keyword detection, bare city+state ZIP lookup fix, Coming Soon listing type end-to-end, and 10-minute real-time alert job with macOS desktop notifications.

## Tasks Completed

| # | Task | Status |
|---|------|--------|
| 1 | Add new filter fields, Coming Soon enum, ZIP fix, and DB migration | Done |
| 2 | Wire new filters into providers, wizard, search filter, and Coming Soon support | Done |
| 3 | Implement real-time saved search alert job with desktop notifications | Done |

## What Was Built

### Task 1 — Models, ZIP Service, Database

**`homesearch/models.py`**
- Added `ListingType.COMING_SOON = "coming_soon"` enum value
- Added `has_fireplace`, `has_ac`, `heat_type`, `has_pool` to `SearchCriteria`
- Added `has_fireplace`, `has_ac`, `heat_type`, `has_pool` to `Listing`

**`homesearch/services/zip_service.py`**
- Added `_STATE_ABBREVS` dict mapping all 50 state names + DC to abbreviations
- Added `_ABBREV_SET` for O(1) lookup
- Rewrote `_parse_city` and `_parse_state` to handle three formats:
  - `"Austin, TX"` (comma-separated — existing behavior preserved)
  - `"Austin TX"` (space-separated with 2-letter abbreviation)
  - `"Austin Texas"` / `"San Antonio Texas"` (space-separated with full state name)
  - Handles 2-word states: `"New York NY"` → city = `"New York"`

**`homesearch/database.py`**
- `init_db()` now runs 4 `ALTER TABLE listings ADD COLUMN` statements wrapped in `try/except` for idempotent migration on existing databases
- `upsert_listing()` INSERT includes the 4 new columns
- `_row_to_listing()` maps the 4 new DB columns to Listing fields

### Task 2 — Providers, Wizard, Filters

**`homesearch/providers/homeharvest_provider.py`**
- Added `ListingType.COMING_SOON: "coming_soon"` to `_LISTING_TYPE_MAP`
- Added description-keyword detection in `_row_to_listing`:
  - `has_fireplace`: `"fireplace"` in description
  - `has_ac`: `"central air"` / `"central a/c"` / `"central ac"` → True; `"no a/c"` / `"window unit"` → False
  - `heat_type`: detects gas, electric, radiant, forced air from description keywords
  - `has_pool`: `"pool"` in description but not `"pool table"` or `"carpool"`
- Passes all 4 new fields to `Listing(...)` constructor

**`homesearch/providers/redfin_provider.py`**
- `_get_listing_type_num`: returns `4` for `COMING_SOON`
- `_home_to_listing`: sets `lt = "coming_soon"` for Coming Soon criteria

**`homesearch/tui/wizard.py`**
- Added `"Coming Soon"` to listing type choices (maps to `ListingType.COMING_SOON`)
- Added 4 new wizard questions after garage spaces, before HOA:
  - Fireplace: Don't care / Must have / No fireplace
  - Air Conditioning: Don't care / Must have / No AC
  - Heat type: Don't care / Gas / Electric / Radiant / Forced Air
  - Pool: Don't care / Must have / No pool
- All 4 new fields passed to `SearchCriteria(...)` constructor
- Summary panel displays all 4 new fields when set

**`homesearch/services/search_service.py`**
- `_passes_filters` extended with 5 new checks:
  - `has_fireplace is True` → listing must have fireplace (None = unknown passes)
  - `has_ac is True` → must have AC; `has_ac is False` → must not have AC
  - `heat_type` (non-"any") → only filters out listings with a known conflicting heat type (unknown passes)
  - `has_pool is True` → must have pool; `has_pool is False` → must not have pool
- Fixed: `listing.id = lid` set after `db.upsert_listing()` so alert job comparisons work correctly

### Task 3 — Real-time Alert Scheduler

**`homesearch/services/scheduler_service.py`**
- Added `IntervalTrigger` import from `apscheduler.triggers.interval`
- Added `alert_job()` function that:
  - Loads all active saved searches via `db.get_saved_searches(active_only=True)`
  - For each search: gets previous listing IDs, runs `run_search()`, compares new results
  - On new listings: sends macOS desktop notification via `osascript` with title + first address + count
  - Logs to stdout: `[Alerts] N new listing(s) for 'search name'`
  - Per-search errors are caught and logged, never abort the job
- Registered with `IntervalTrigger(minutes=10)` as `"realtime_alerts"` job

## Verification Results

All checks passed:

```
All model + ZIP checks passed
All filter + Coming Soon checks passed
Alert trigger: interval[0:10:00]
Scheduler alert job verified
Models OK
ZIP fix OK
Filters OK
Scheduler OK
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all features are fully wired end-to-end.

## Self-Check: PASSED

All modified files verified to exist and contain expected implementations. All verification assertions passed via `uv run python`.
