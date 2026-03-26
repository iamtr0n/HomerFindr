---
phase: quick
plan: 260326-gal
subsystem: scoring
tags: [scoring, badges, gold-star, cli, frontend, pagination]
dependency_graph:
  requires: []
  provides: [match_score, match_badges, is_gold_star, best_match_sort]
  affects: [homesearch/models.py, homesearch/services/search_service.py, homesearch/tui/results.py, homesearch/tui/wizard.py, frontend/src/pages/NewSearch.jsx, frontend/src/components/PropertyCard.jsx]
tech_stack:
  added: []
  patterns: [scoring_engine, badge_system, pagination]
key_files:
  created: []
  modified:
    - homesearch/models.py
    - homesearch/services/search_service.py
    - homesearch/tui/results.py
    - homesearch/tui/wizard.py
    - frontend/src/pages/NewSearch.jsx
    - frontend/src/components/PropertyCard.jsx
decisions:
  - "_perfect_score computed as count of non-None optional criteria to normalize gold star threshold per-search"
  - "CLI url_map built across all results (not just current page) so pagination doesn't break URL selection"
  - "isGoldStar computed in NewSearch.jsx from max match_score across all results and passed as prop to PropertyCard"
metrics:
  duration: ~8 minutes
  completed_date: "2026-03-26T15:50:46Z"
  tasks_completed: 2
  files_modified: 6
---

# Quick Task 260326-gal: Scoring Engine, Match Badges, Gold Star Summary

**One-liner:** Scoring engine scoring listings by optional-criteria satisfaction, with gold star status, badge chips, sorted results, and paginated CLI/web display.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Scoring engine, model fields, sorted results, CLI upgrades | 1d75334 | models.py, search_service.py, results.py, wizard.py |
| 2 | Web frontend — Best Match sort, gold star, badges, Load More | 50281c7 | NewSearch.jsx, PropertyCard.jsx |

## What Was Built

### Task 1: Backend + CLI

**Model fields** (`homesearch/models.py`):
- Added `match_score: int = 0`, `match_badges: list[str] = Field(default_factory=list)`, `is_gold_star: bool = False` to `Listing`

**Scoring engine** (`homesearch/services/search_service.py`):
- `_score_listing(listing, criteria)` — awards badge strings for: garage, basement, pool, fireplace, A/C, HOA compliance, bed/bath match, price in range, new build (>=2020), heat type match. Score = len(badges).
- `_perfect_score(criteria)` — counts non-None optional criteria fields to establish gold star threshold per search.
- `run_search()` scores all filtered listings, marks `is_gold_star = score >= perfect`, then sorts: gold_star DESC, match_score DESC, price ASC.

**CLI results** (`homesearch/tui/results.py`):
- Added star (★), Score, and Badges columns to the results table.
- Paginated display: 50 listings per page with "Show 50 more?" prompt between pages.
- URL selection prompt loops back after opening a URL — only exits when user picks "Back to menu".
- url_map built across all results (not page-scoped) so numbered entries remain correct.

**CLI wizard** (`homesearch/tui/wizard.py`):
- Replaced single `questionary.select` price range with `questionary.checkbox` multi-select.
- Added `_parse_multi_price()` helper: combines selected ranges to price_min = min of all selected mins, price_max = max of all selected maxes.
- "Custom range" option prompts two text inputs for manual min/max entry.
- New price ranges: Under $200k / $200k-$350k / $350k-$500k / $500k-$750k / $750k-$1M / Over $1M / Custom.

### Task 2: Frontend

**NewSearch.jsx**:
- Default `sortBy` changed from `'price_asc'` to `'best_match'`.
- Added `visibleCount` state (default 50), reset to 50 on each new search.
- `sortedResults()` extended with `best_match` case using gold star then score then price ordering.
- `perfectScore` computed as `Math.max(...scores)` across all results.
- Gold star count shown as "⭐ N Perfect Matches" section header when any exist.
- Grid sliced to `visible = sorted.slice(0, visibleCount)`.
- "Load 50 more" button increments `visibleCount` by 50 when more results remain.
- "← Back to search" button resets `results` to null, re-showing the search form.
- `isGoldStar` computed per-listing and passed as prop to `PropertyCard`.

**PropertyCard.jsx**:
- Accepts `isGoldStar = false` prop.
- Gold star cards get `ring-2 ring-amber-400 border-amber-300` on the Card wrapper.
- "⭐ Perfect Match" amber badge added at `top-2 left-2` when `isGoldStar`.
- `match_badges` rendered as blue chip pills (`bg-blue-50 text-blue-700 border-blue-200`) above the features badges row.

## Deviations from Plan

None — plan executed exactly as written. Badge logic in `_score_listing` follows the plan spec precisely (criteria-gated badges, not listing-always badges). The `_perfect_score` function counts all active optional criteria correctly.

## Verification

- `uv run python -c "from homesearch.services.search_service import _score_listing; print('import OK')"` — PASSED
- Scoring test: `score=3, badges=['garage', 'basement', 'price ✓']` for matching criteria — PASSED
- `model_fields OK` (match_score, match_badges, is_gold_star all present) — PASSED
- `npx vite build --mode production` — PASSED (276 kB, built in 783ms, 0 errors)

## Known Stubs

None — all data flows from `_score_listing` through `run_search` to both CLI and API response. The `match_badges` and `match_score` fields are serialized by Pydantic and returned in the API JSON response, consumed directly by the frontend.

## Self-Check: PASSED

Files verified present:
- homesearch/models.py — modified with 3 new fields
- homesearch/services/search_service.py — _score_listing, _perfect_score added, run_search wired
- homesearch/tui/results.py — pagination + score/badge columns + back-nav loop
- homesearch/tui/wizard.py — _parse_multi_price added, checkbox price wizard
- frontend/src/pages/NewSearch.jsx — best_match sort, visibleCount, Load More, Back to search
- frontend/src/components/PropertyCard.jsx — isGoldStar prop, gold star badge, match_badges chips

Commits verified:
- 1d75334 — feat(260326-gal-1): scoring engine, match badges, gold star, CLI upgrades
- 50281c7 — feat(260326-gal-2): web UI — Best Match sort, gold star badges, match chips, Load More
