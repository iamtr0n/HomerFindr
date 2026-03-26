---
phase: quick
plan: 260326-j1t
subsystem: homeharvest-provider
tags: [bug-fix, performance, listing-type, coming-soon, homeharvest]
dependency_graph:
  requires: []
  provides: [working-coming-soon-search, batched-listing-type-calls]
  affects: [homesearch/providers/homeharvest_provider.py]
tech_stack:
  added: []
  patterns: [batch-api-calls, listing-type-mapping]
key_files:
  modified:
    - homesearch/providers/homeharvest_provider.py
decisions:
  - "Map COMING_SOON to 'pending' (homeharvest valid type) — homeharvest has no 'coming_soon' ListingType"
  - "Batch multiple listing types into a single scrape_property call per location using list arg"
  - "Pass past_days=30 only when 'sold' is present in batched hh_types list"
  - "Use hh_types[0] as default_lt for _row_to_listing when multiple types are batched"
metrics:
  duration: "< 5 minutes"
  completed: "2026-03-26"
  tasks_completed: 1
  files_modified: 1
---

# Quick Task 260326-j1t: Fix Coming Soon InvalidListingType Error

**One-liner:** Map COMING_SOON to homeharvest's "pending" type and batch multi-type searches into one API call per location.

## What Was Done

Fixed two issues in `homesearch/providers/homeharvest_provider.py`:

### Fix 1: _LISTING_TYPE_MAP correction

`ListingType.COMING_SOON` was mapped to `"coming_soon"` which is not a valid homeharvest `ListingType` enum value. The valid values are: `for_sale`, `for_rent`, `sold`, `pending`. Changed the mapping to `"pending"` which represents pre-market/coming-soon listings in homeharvest.

### Fix 2: Batched listing types per location

The `search()` method previously nested loops as `for lt_enum in types_to_run` → `for location in locations`, making `len(types) * len(locations)` API calls. Refactored to:

1. Build a deduplicated list of homeharvest type strings (`hh_types`)
2. Pass the full list to a single `scrape_property(listing_type=hh_types)` call per location
3. Only include `past_days=30` when `"sold"` is among the batched types
4. Progress tracking now counts `len(locations)` steps (not types × locations)

## Commits

| Hash | Description |
|------|-------------|
| 5dfa8d0 | fix(260326-j1t): fix coming_soon InvalidListingType and batch listing types per location |

## Verification

All plan assertions passed:
- `_LISTING_TYPE_MAP[ListingType.COMING_SOON] == "pending"` — confirmed
- All mapped values are in `{"for_sale", "for_rent", "sold", "pending"}` — confirmed
- Module imports without errors — confirmed

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- File exists: `homesearch/providers/homeharvest_provider.py` — FOUND
- Commit 5dfa8d0 exists — FOUND
