---
phase: quick
plan: 260326-gam
subsystem: search-enrichment
tags: [highway-proximity, school-ratings, sectioned-results, overpass-api]
dependency_graph:
  requires: [models, search_service, homeharvest_provider, SearchForm, PropertyCard, NewSearch]
  provides: [road_service, school_service, highway-filtering, school-filtering, sectioned-results-ui]
  affects: [search-pipeline, results-display, advanced-filters]
tech_stack:
  added: [OpenStreetMap Overpass API]
  patterns: [module-level-cache, waterfall-section-grouping, conditional-enrichment]
key_files:
  created:
    - homesearch/services/road_service.py
    - homesearch/services/school_service.py
  modified:
    - homesearch/models.py
    - homesearch/services/search_service.py
    - homesearch/providers/homeharvest_provider.py
    - frontend/src/components/SearchForm.jsx
    - frontend/src/components/PropertyCard.jsx
    - frontend/src/pages/NewSearch.jsx
decisions:
  - School ratings extracted at provider level from homeharvest row data rather than separate API call
  - Highway enrichment runs only when avoid_highways is enabled to avoid unnecessary API calls
  - Overpass API used for highway detection with 200m radius and module-level cache
metrics:
  duration: 3m
  completed: "2026-03-26T15:56:14Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 8
---

# Quick Task 260326-gam: Highway Proximity Detection + School Ratings Summary

Highway proximity detection via Overpass API with module-level caching, school rating extraction from homeharvest data, and collapsible sectioned results grouped by match quality.

## What Was Done

### Task 1: Backend services and model extensions (b646431)

- Extended `SearchCriteria` with `avoid_highways: bool` and `school_rating_min: Optional[int]`
- Extended `Listing` with `near_highway`, `highway_name`, `school_rating`, `school_district` fields
- Created `road_service.py` -- queries OpenStreetMap Overpass API for motorway/trunk/primary roads within 200m, caches by rounded lat/lon, fails gracefully
- Created `school_service.py` -- extracts school ratings from homeharvest DataFrame rows using known column names
- Updated `search_service.py` -- highway enrichment after filtering (conditional on avoid_highways), school_rating_min filter in _passes_filters, highway-near listings sorted to end
- Updated `homeharvest_provider.py` -- extracts school_rating and school_district from row data

### Task 2: Frontend form controls and sectioned results (a21e071)

- Added "Avoid highways" checkbox and "Min School Rating" select (1-10) in SearchForm advanced filters
- Added highway warning badge (amber) and school rating in PropertyCard features list
- Replaced flat results grid with collapsible sectioned display: Perfect Match (open), Strong Match (open), Good Options (collapsed), Near Highway (collapsed)
- Each section has colored header with icon, title, count, and show/hide toggle

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] School service simplified to row extraction**
- **Found during:** Task 1
- **Issue:** Plan suggested GreatSchools scraping or Overpass school queries, both fragile/unreliable for ratings
- **Fix:** Simplified school_service to extract ratings from homeharvest data rows when columns exist
- **Files modified:** homesearch/services/school_service.py
- **Commit:** b646431

## Verification Results

- All model fields verified with Python assertions
- Services importable and callable
- Frontend builds successfully (vite build, 995ms)

## Known Stubs

None -- all data flows are wired. School ratings will populate when homeharvest returns school-related columns in its DataFrame; otherwise they gracefully default to None.
