# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## homerfindr-empty-search-results — Search returns zero results due to Redfin 403 + silent over-filtering
- **Date:** 2026-03-26
- **Error patterns:** empty results, no properties found, 403 Forbidden, Redfin blocked, zero listings, spinner completes no results, passes_filters removes all
- **Root cause:** Two compounding causes: (1) Redfin stingray API returns 403 Forbidden for all requests — silently contributes zero listings with no user warning. (2) _passes_filters() removes ALL listings when user selects criteria too restrictive for their area (e.g. price_max below market) — the "No properties found" message gives no indication of whether zero results came from no data vs. over-filtering.
- **Fix:** (1) RedfinProvider catches 403 specifically and prints a single "[Redfin] API access blocked (403)" message instead of per-ZIP tracebacks. (2) run_search() accepts pre_filter_counts list parameter populated before client-side filtering. execute_search_with_spinner() returns (list[Listing], int) tuple with pre_filter_count. display_results() shows active filters and pre-filter count when results are empty but pre_filter_count > 0, vs. "no data found" message when pre_filter_count=0. menu.py and saved_browser.py updated to unpack tuple.
- **Files changed:** homesearch/services/search_service.py, homesearch/tui/results.py, homesearch/providers/redfin_provider.py, homesearch/tui/menu.py, homesearch/tui/saved_browser.py
---

