---
phase: 03-web-ui-redesign
plan: 01
subsystem: backend-api
tags: [bug-fix, database, api, dedup, tailwind]
dependency_graph:
  requires: []
  provides: [working-preview-endpoint, accurate-result-count, pinned-tailwind, enhanced-dedup, provider-errors-in-api]
  affects: [homesearch/database.py, homesearch/services/search_service.py, homesearch/api/routes.py, frontend/src/api.js, frontend/package.json]
tech_stack:
  added: []
  patterns: [COALESCE subquery for count, optional errors accumulator param, regex-based address normalization]
key_files:
  created: []
  modified:
    - frontend/src/api.js
    - frontend/package.json
    - homesearch/database.py
    - homesearch/services/search_service.py
    - homesearch/api/routes.py
decisions:
  - FIX-01 was a false alarm — api.js previewSearch already used correct path; documented with comment
  - FIX-03 uses COALESCE subquery in all three get_saved_search* functions rather than a separate query
  - XC-02 uses optional accumulator pattern (errors=None) for full backward compatibility
  - XC-01 uses re.sub for unit stripping + string replace for suffix/directional normalization
metrics:
  duration: ~15 min
  completed: "2026-03-25"
  tasks: 2
  files_modified: 5
---

# Phase 03 Plan 01: Bug Fixes and Backend Cross-Cutting Features Summary

**One-liner:** Fixed preview endpoint (verified correct), pinned Tailwind to ~3.4, added COALESCE subquery for result_count in all saved search queries, and added provider error collection + enhanced address dedup to search service.

## What Was Built

This plan fixed three blocking bugs and added two backend improvements before any visual redesign work begins.

**FIX-01 — Preview endpoint 404 (verified, no fix needed):**
After reading `frontend/src/api.js`, `homesearch/api/routes.py`, and `frontend/vite.config.js`, the paths were confirmed to already match. `BASE='/api'` + `'/search/preview'` → `fetch('/api/search/preview')`. Vite proxies `/api/*` → `http://127.0.0.1:8000/api/*`. Backend has `@app.post("/api/search/preview")`. No double prefix. Added a comment to document this verification.

**FIX-04 — Tailwind CSS version pin:**
Changed `"tailwindcss": "^3.4.7"` to `"~3.4.7"` in `frontend/package.json`. The `~` prefix allows patch updates (3.4.x) but blocks minor (3.5.0) and major (4.0.0) upgrades. Note: a parallel agent added `clsx` and `tailwind-merge` to the file mid-execution; the Tailwind pin was re-applied to the updated file.

**FIX-03 — result_count subquery:**
All three saved search query functions (`get_saved_searches`, `get_saved_search`, `get_saved_search_by_name`) were updated to use a COALESCE subquery that counts rows from `search_results` rather than returning zero. The `result_count=row["result_count"]` field mapping was added to each `SavedSearch` constructor call.

**XC-02 — Provider error collection:**
`run_search` now accepts an optional `errors: Optional[list] = None` parameter. When a provider raises an exception, the error message `"{provider.name}: {e}"` is appended to the list if provided. All three API routes (`preview_search`, `create_and_run_search`, `run_saved_search`) collect errors and include them in `SearchResponse.provider_errors`.

**XC-01 — Enhanced address deduplication:**
`_normalize_address` now uses `re.sub` to strip unit/apt/suite designators before suffix normalization, and also normalizes directional words (north/south/east/west and their compounds) to abbreviations. `import re` was added at module level.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | FIX-01 preview endpoint, FIX-04 Tailwind pin, FIX-03 result_count | 6f59426 | frontend/src/api.js, frontend/package.json, homesearch/database.py |
| 2 | XC-02 provider error collection, XC-01 enhanced dedup | fe1921e | homesearch/services/search_service.py, homesearch/api/routes.py |

## Deviations from Plan

### Auto-fixed Issues

None.

### Noted Deviations

**1. FIX-01 was a no-op (paths already correct)**
- **Found during:** Task 1 — reading api.js, routes.py, vite.config.js
- **Issue:** STATE.md noted "double /api prefix 404" but actual code had no double prefix
- **Fix:** Added a comment to api.js documenting the verified-correct path to prevent future confusion
- **Files modified:** frontend/src/api.js

**2. Parallel agent modified package.json mid-execution**
- **Found during:** Task 1 — post-commit notification showed package.json was modified by another process
- **Issue:** Another agent added `clsx` and `tailwind-merge` dependencies and reset tailwindcss to `^3.4.7`
- **Fix:** Re-read the file and re-applied the `~3.4.7` pin to the updated file. The added dependencies (`clsx`, `tailwind-merge`) are appropriate for the Phase 03 web UI redesign.

## Known Stubs

None — all changes are backend/config fixes with no UI rendering paths involved.

## Self-Check: PASSED

Files verified:
- FOUND: frontend/src/api.js (previewSearch comment present)
- FOUND: frontend/package.json (~3.4.7 Tailwind pin present)
- FOUND: homesearch/database.py (COALESCE subquery, result_count=row in 3 functions)
- FOUND: homesearch/services/search_service.py (errors param, re import, enhanced _normalize_address)
- FOUND: homesearch/api/routes.py (provider_errors field + 3 route usages)

Commits verified:
- FOUND: 6f59426 (Task 1)
- FOUND: fe1921e (Task 2)
