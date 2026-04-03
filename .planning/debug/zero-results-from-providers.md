---
status: awaiting_human_verify
trigger: "HomerFindr returns zero results from providers on both CLI and web interfaces"
created: 2026-03-27T10:00:00Z
updated: 2026-03-27T12:30:00Z
---

## Current Focus

hypothesis: CONFIRMED — Two compounding root causes identified and fixed: (1) Silent exception swallowing in HomeHarvestProvider per-ZIP loop — errors never surfaced to provider_errors. (2) Web SSE stream takes 4+ minutes for city-level searches (169 ZIPs × 1.5s rate limit) — frontend never received the results event before user abandoned. Fixed both: on_error callback surfaces ZIP errors to provider_errors; on_partial callback streams listings to the frontend as each ZIP completes so results appear within seconds.
test: Build passes (vite build clean). on_partial wired in routes.py; api.js handles partial events; NewSearch.jsx accumulates partial listings and shows them live while loading.
expecting: Human to confirm fix works in their real workflow — results should now appear within seconds of search start, updating as more ZIPs complete
next_action: Human verification — restart server and test a city-level search

## Symptoms

expected: Search returns listings from Realtor.com (homeharvest provider)
actual: Zero listings returned from providers — both CLI and web browser show empty results
errors: "No listings returned from providers" or equivalent empty result
reproduction: Run any search (For Sale, any ZIP, any criteria) — zero results shown with no error message
started: After recent changes to homeharvest_provider.py that added server-side filter params (exclude_pending, price_min/max, beds_min/max, sqft_min/max, lot_sqft_min, year_built_min)

## Eliminated

- hypothesis: New filter params are invalid for installed homeharvest version
  evidence: All params confirmed valid via inspect.signature() on both uv venv and Homebrew venv
  timestamp: 2026-03-27T10:10:00Z

- hypothesis: homeharvest itself returns zero results
  evidence: Direct call scrape_property(location='11746') returns 83 results in both venvs
  timestamp: 2026-03-27T10:15:00Z

- hypothesis: All-None filter params cause zero results
  evidence: scrape_property with all params=None returns 83 results
  timestamp: 2026-03-27T10:16:00Z

- hypothesis: listing_type as list causes zero results
  evidence: scrape_property(listing_type=['for_sale']) returns 83 results
  timestamp: 2026-03-27T10:17:00Z

- hypothesis: HomeHarvestProvider.search() returns zero end-to-end
  evidence: Direct provider call returns 83 results; run_search returns 81-155 results
  timestamp: 2026-03-27T10:20:00Z

- hypothesis: Homebrew install uses stale/different code
  evidence: Homebrew libexec IS the repo directory (symlinked). Editable install via .pth file points directly to repo source
  timestamp: 2026-03-27T10:25:00Z

- hypothesis: listing_type safety net filters out all results
  evidence: homeharvest returns status='FOR_SALE' for all for-sale results; _row_to_listing maps this to lt='sale'; safety net passes all
  timestamp: 2026-03-27T10:40:00Z

- hypothesis: MLS status override tags for-sale listings as wrong type
  evidence: 'FOR_SALE' matches none of the override conditions (PENDING/CONTINGENT/COMING_SOON/FOR_RENT/SOLD); lt stays 'sale'
  timestamp: 2026-03-27T10:45:00Z

- hypothesis: Specific filter value combinations cause zero
  evidence: Tested beds_min=3, price_max=500000, sqft_min/max, year_built_min, lot_sqft_min, baths_min — all return results
  timestamp: 2026-03-27T11:00:00Z

- hypothesis: Frontend build mismatch
  evidence: Built JS contains search/stream, onResults, onProgress, listing_types — all correct
  timestamp: 2026-03-27T11:10:00Z

- hypothesis: Rate limiting by Realtor.com causing empty responses
  evidence: Sequential calls to 5 different ZIPs all return results; no degradation observed
  timestamp: 2026-03-27T11:15:00Z

## Evidence

- timestamp: 2026-03-27T10:30:00Z
  checked: Live SSE stream with frontend payload
  found: Stream processes 169 ZIPs (zip discovery for '11746' with 25mi radius), returns total:81
  implication: Search works but takes ~4+ minutes; connection dropped by curl at 2min timeout

- timestamp: 2026-03-27T11:20:00Z
  checked: git status — uncommitted working tree changes
  found: homeharvest_provider.py (new filter params), search_service.py (safety net removed), wizard.py (back nav), frontend files (style)
  implication: All uncommitted; server started after changes were written (10:30AM > 20:40 yesterday) so server has current code

- timestamp: 2026-03-27T11:25:00Z
  checked: provider_errors flow — what reaches the user
  found: HomeHarvestProvider.search() catches all its own exceptions internally (except Exception: traceback.print_exc(); continue). The run_search() outer catch only fires if provider.search() itself throws — which it never does. So provider_errors is always [] even when every ZIP fails silently.
  implication: This is the root cause: silent failure mode with no user-visible error

- timestamp: 2026-03-27T11:35:00Z
  checked: Fix verification via monkey-patch
  found: With failing scrape_property, errors now correctly surface as "realtor/11746: Simulated network failure" in the errors list; provider_errors shows in web UI
  implication: Fix works; errors now reach the user when homeharvest fails

- timestamp: 2026-03-27T12:00:00Z
  checked: Live SSE stream timing — 169 ZIPs × 1.5s rate limit sleep
  found: City-level search takes 4+ minutes minimum before the results event fires; frontend shows empty until then
  implication: Second root cause for "zero results on web" — user sees nothing for 4+ minutes, likely abandons or assumes broken

- timestamp: 2026-03-27T12:30:00Z
  checked: on_partial callback wiring in routes.py, api.js, NewSearch.jsx
  found: on_partial pushes partial events through SSE queue as each ZIP batch completes; frontend accumulates and renders listings live; final results event replaces partial preview with deduped/scored/sorted list. Frontend build clean (vite build, 920ms, no errors).
  implication: Users now see first results within seconds of search start; the 4-minute wait is no longer a UX blocker

## Resolution

root_cause: Two compounding causes: (1) Silent exception swallowing in HomeHarvestProvider.search() per-ZIP loop — when scrape_property() raises, exception is caught and printed to stdout but returns 0 for that ZIP; since search() never raises itself, run_search()'s outer catch never fires and provider_errors stays empty forever. (2) Web SSE stream for city-level searches requires all 169 ZIPs to complete (169 × 1.5s = 4+ minutes) before the results event is sent — the frontend showed nothing until then, so users saw "0 results" if they waited or an empty state if they gave up.

fix: (1) Added on_error callback to HomeHarvestProvider.search() that fires per failing ZIP; run_search() wires _on_error to collect zip_errors into provider_errors list (visible in web UI yellow banner and CLI). (2) Wired on_partial callback in routes.py stream_search route to push partial listing batches through the SSE queue as intermediate partial events; api.js handles partial event type; NewSearch.jsx accumulates partial listings and renders them live while loading=true, replacing with final authoritative results when the results event arrives.

verification: Monkey-patch test confirms on_error surfaces correctly. Frontend build passes clean. Live API returns 81 results for single-ZIP tests. Server restart required to pick up search_service.py and routes.py changes.

files_changed:
  - homesearch/providers/homeharvest_provider.py: Added on_error=None parameter to search(); calls on_error(location, exc) in exception handler
  - homesearch/services/search_service.py: Added _on_error callback that collects zip_errors; passes on_error=_on_error to provider.search(); extends errors list with zip_errors
  - homesearch/api/routes.py: Added on_partial callback that pushes partial events through SSE queue; passes on_partial to run_search()
  - frontend/src/api.js: Added onPartial parameter to streamSearch(); dispatches partial events to onPartial handler
  - frontend/src/pages/NewSearch.jsx: Added onPartial handler that accumulates partial listings into live results preview; results panel now visible during loading when partials exist; sort dropdown hidden until final results arrive; counter shows "found so far…" during streaming
