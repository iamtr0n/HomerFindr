---
quick_task: 260326-qyh
title: Smart Enhancements — Listing Type Filter + Feature Additions
date: 2026-03-26
commits:
  - 003b228
  - 5f34f9f
  - 0e6c5fa
  - ce831f7
  - fa85350
tags: [filtering, ui, cli, scoring, property-card]
key-files:
  modified:
    - homesearch/services/search_service.py
    - frontend/src/components/SearchForm.jsx
    - frontend/src/pages/SearchResults.jsx
    - frontend/src/components/PropertyCard.jsx
    - homesearch/tui/results.py
decisions:
  - listing_type guard placed at top of _passes_filters() before all other checks for maximum safety
  - listing_types array sent from frontend (not legacy listing_type scalar) to support multi-select
  - DOM badge shown inline with price row in PropertyCard (not as separate badge) to keep card compact
  - DomBadge skips 8-30 day range (normal market time, no badge needed)
  - Detail card shows Days on Market for all listing types; pending section retains its agent/warning block
---

# Quick Task 260326-qyh: Smart Enhancements Summary

**One-liner:** Listing type safety net in search filter + Pending multi-select UI + Best Match default sort + PropertyCard score chip/type badge/price-per-sqft/DOM badge + CLI price/sqft and DOM indicators.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add listing_type safety net to `_passes_filters()` | 003b228 | `search_service.py` |
| 2 | Add Pending + multi-select listing types to SearchForm | 5f34f9f | `SearchForm.jsx` |
| 3 | Add Best Match sort as default in SearchResults | 0e6c5fa | `SearchResults.jsx` |
| 4 | PropertyCard: score chip, listing type badge, price/sqft, DOM badge | ce831f7 | `PropertyCard.jsx` |
| 5 | CLI results: price/sqft and DOM indicator in selector + detail card | fa85350 | `results.py` |

## What Was Built

### Task 1 — Listing Type Filter Safety Net
Added a guard at the top of `_passes_filters()` that rejects any listing whose `listing_type` doesn't match the criteria. Supports both `criteria.listing_type` (single) and `criteria.listing_types` (multi-select array). This prevents pending/coming_soon listings from ever appearing in for-sale results even if a provider returns unexpected data.

### Task 2 — Pending + Multi-Select Listing Types
- Added `pending` to `LISTING_TYPES` (5 types total, parity with CLI)
- Replaced single `listing_type` state with `listingTypes` array initialized to `['sale']`
- Added `toggleListingType()` — clicks toggle individual types on/off, minimum 1 must remain selected
- Button group now highlights all selected types simultaneously
- `buildCriteria()` sends `listing_types` array instead of scalar `listing_type`

### Task 3 — Best Match Default Sort
- Added `{ value: 'match_score', label: 'Best Match' }` as first option in sort dropdown
- Default `sortBy` state changed from `'price_asc'` to `'match_score'`
- Sort logic: descending by `match_score`, ties broken by `is_gold_star`

### Task 4 — PropertyCard Enhancements
- `LISTING_TYPE_STYLES` map: colored pills for sale (green), pending (amber), coming_soon (blue), rent (purple), sold (gray)
- `DomBadge` component: green "New" for <7 days, amber "X days" for 31-60, red "X days" for 60+, no badge for 8-30
- Listing type badge rendered on bottom-left of photo area
- Score chip `{N} match` shown inline next to price when match_score > 0
- DOM badge inline with price/score row
- `$X/sqft` added to stats row when both price and sqft are present

### Task 5 — CLI Results Enhancements
- Selector list: `($X/sf)` shown after price column; DOM emoji indicators appended (🟢New, 🟡Xd, 🔴Xd)
- Detail card: price row gets `($X/sqft)` dim suffix when both fields present
- Detail card: "Days on Market" row added for all listing types with Rich color coding (green/yellow/red)

## Deviations from Plan

None — plan executed exactly as written. The constraints document provided exact implementation details that were followed precisely.

## Build Verification

Frontend build: vite v5.4.21 — 1613 modules, built in 964ms. No errors.
Python rsync: completed successfully to `/opt/homebrew/Cellar/homerfindr/1.1.0/libexec/homesearch/`.

## Known Stubs

None. All features wire to real data fields already present in the `Listing` model (`listing_type`, `match_score`, `match_badges`, `days_on_mls`, `price`, `sqft`, `is_gold_star`).
