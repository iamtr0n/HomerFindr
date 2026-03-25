---
phase: 03-web-ui-redesign
plan: 04
subsystem: frontend
tags: [filters, provider-errors, responsive, ux]
dependency_graph:
  requires: [03-01, 03-02]
  provides: [WEB-04, WEB-05, XC-02-frontend]
  affects: [frontend/src/pages/SearchResults.jsx, frontend/src/pages/NewSearch.jsx]
tech_stack:
  added: []
  patterns: [client-side-filtering, amber-warning-banner, brand-color-consistency]
key_files:
  created: []
  modified:
    - frontend/src/pages/SearchResults.jsx
    - frontend/src/pages/NewSearch.jsx
decisions:
  - "filteredAndSorted() replaces sortedResults() — single function handles both filtering and sorting client-side, no additional API calls"
  - "Amber (amber-50/200/700/800) chosen for provider error banner — visually distinct from brand green, universally understood as warning color"
  - "filter inputs use uncontrolled number type with empty string default — allows clearing filter by emptying the field"
metrics:
  duration: 5 minutes
  completed_date: "2026-03-25T23:49:45Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 03 Plan 04: Filter Controls and Provider Error Banner Summary

Client-side filter bar (price range, beds, baths) added to SearchResults; amber provider error banner wired to API `provider_errors` in both SearchResults and NewSearch; all blue-600 replaced with brand colors in plan-scoped files.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add filter controls and provider error banner to SearchResults | 113c140 | frontend/src/pages/SearchResults.jsx |
| 2 | Add provider error banner to NewSearch and update styling | 39e554b | frontend/src/pages/NewSearch.jsx |

## What Was Built

### Task 1 — SearchResults filter controls and provider error banner

Added four client-side filter state hooks (`filterMinPrice`, `filterMaxPrice`, `filterMinBeds`, `filterMinBaths`) and a `providerErrors` state populated from `runMutation.onSuccess`. Replaced the old `sortedResults()` function with `filteredAndSorted()` that applies filters then sort in sequence — no API calls triggered on filter change.

Filter bar now contains: New Only toggle, price range (min/max number inputs with DollarSign icon), beds dropdown (1–5+), baths dropdown (1–3+), sort dropdown, and a live result count showing filtered vs total. Provider error banner renders above the filter bar in amber when `providerErrors.length > 0`.

Replaced both `bg-blue-600` raw buttons with the `Button` component (`variant="default"` uses brand-600). Replaced `text-blue-500` spinner with `text-brand-500`. Responsive grid (`xl:grid-cols-4`) preserved.

### Task 2 — NewSearch provider error banner and responsive fixes

Added `providerErrors` state extracted from `data.provider_errors` in `handleResults`. Amber banner renders between the search form and results when errors exist and loading is false. Results heading flex container changed from `flex justify-between` to `flex flex-wrap justify-between items-center gap-2` for mobile wrapping. Loading spinner updated from `text-blue-600` to `text-brand-600`. Sort dropdown border updated to `border-slate-200`.

## Decisions Made

1. `filteredAndSorted()` replaces `sortedResults()` — single function handles both filtering and sorting client-side, no additional API calls
2. Amber (amber-50/200/700/800) chosen for provider error banner — visually distinct from brand green, universally understood as warning color
3. Filter inputs use empty string default with `+value` coercion — allows clearing by emptying the field without special null handling

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both provider error banners are wired to live API data (`provider_errors` from `SearchResponse` added in Plan 01). Filter controls operate on real results data.

## Out-of-Scope Note

`Dashboard.jsx` still contains `bg-blue-600` classes — this file was explicitly out of scope for this plan (plan frontmatter lists only SearchResults.jsx and NewSearch.jsx). Logged for a future cleanup plan.

## Self-Check: PASSED

- frontend/src/pages/SearchResults.jsx: FOUND
- frontend/src/pages/NewSearch.jsx: FOUND
- Commit 113c140: FOUND
- Commit 39e554b: FOUND
- Vite build: PASSED (909ms, 0 errors)
