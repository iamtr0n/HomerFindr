---
status: resolved
trigger: "Search wizard completes with spinner but returns zero listings. Never returned results — this is the first time testing."
created: 2026-03-26T00:00:00Z
updated: 2026-03-26T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED - Two root causes found:
  (1) Redfin provider always returns 403 Forbidden - zero results from Redfin, silently swallowed
  (2) _passes_filters silently removes ALL listings when user picks restrictive criteria (price_max, property_types) that don't match their area - zero feedback to user about why
test: Verified both causes through direct testing
expecting: N/A - root causes confirmed
next_action: Apply fix - show active filters in "no results" message + disable Redfin gracefully

## Symptoms

expected: Search wizard returns property listings from Realtor.com (homeharvest) and/or Redfin providers
actual: Search runs (spinner shows), completes, says "No properties found matching your criteria"
errors: None visible to user — no tracebacks shown in TUI
reproduction: Run `uv run python -m homesearch.main`, complete search wizard, observe empty results
started: Never worked — first time testing

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-03-26T00:01:00Z
  checked: search_service.py run_search() flow
  found: Providers wrapped in try/except — exceptions print to console but are swallowed. Results can be empty if ALL providers throw or return [].
  implication: The TUI spinner thread captures stdout separately from Rich Live; error messages from providers may not be visible to user at all.

- timestamp: 2026-03-26T00:01:00Z
  checked: results.py execute_search_with_spinner()
  found: run_search() called with use_zip_discovery=True even though wizard already discovered ZIPs and put them in criteria.zip_codes. search_service.resolve_zip_codes() short-circuits if criteria.zip_codes is already populated, so double-discovery is NOT the problem.
  implication: ZIP discovery is fine. The real issue is in what the providers do with those ZIP codes.

- timestamp: 2026-03-26T00:02:00Z
  checked: redfin package - client.search('10001') direct call
  found: EXCEPTION: HTTPError: 403 Client Error: Forbidden for url: https://redfin.com/stingray/do/location-autocomplete?location=10001&v=2
  implication: Redfin stingray API is 403 blocked — the redfin package no longer works. Zero results from Redfin always. This silently reduces provider coverage by 50%.

- timestamp: 2026-03-26T00:03:00Z
  checked: homeharvest.scrape_property('10001', 'for_sale') direct call
  found: 119 rows returned. Full pipeline HomeHarvestProvider.search() returns 119 listings.
  implication: homeharvest works correctly. NOT the cause of zero results.

- timestamp: 2026-03-26T00:04:00Z
  checked: run_search() end-to-end with both providers
  found: Returns 69 results (after dedup) despite Redfin 403. homeharvest alone is sufficient.
  implication: Pipeline works correctly. Zero results must come from _passes_filters removing everything.

- timestamp: 2026-03-26T00:05:00Z
  checked: _passes_filters with price_max=50000 in Austin TX
  found: run_search returns 0 results. Only 1 listing in ZIP 78660 has price < $50k. With deduplication across ZIPs it rounds to zero.
  implication: CONFIRMED ROOT CAUSE: user selected price range (or other filter) that removes all listings in their area. _passes_filters gives zero feedback about what was filtered.

- timestamp: 2026-03-26T00:06:00Z
  checked: display_results() in results.py
  found: When results=[], prints "[yellow]No properties found matching your criteria.[/yellow]" with no information about active filters or how many listings were found before filtering.
  implication: User has no way to know whether zero results came from no data or over-filtering.

- timestamp: 2026-03-26T00:07:00Z
  checked: execute_search_with_spinner threading pattern
  found: Thread correctly extends results[] before setting done_event. join(timeout=1.0) after event fires. Pattern is sound - 252 results confirmed in thread test.
  implication: Threading is NOT the cause. Results genuinely empty when returned.

## Eliminated

- hypothesis: Redfin meta_property() method missing or API changed
  evidence: meta_property() EXISTS on Redfin client. Fails with 403, not AttributeError. Exception caught per-location in provider loop.
  timestamp: 2026-03-26T00:02:00Z

- hypothesis: homeharvest package broken or returns wrong schema
  evidence: Returns 119 rows for ZIP 10001, 639 for ZIP 78660. Column 'street' exists and maps correctly. _row_to_listing produces valid Listing objects.
  timestamp: 2026-03-26T00:03:00Z

- hypothesis: Threading race condition in execute_search_with_spinner
  evidence: results.extend(found) happens before done_event.set(). Tested directly - 252 results returned from thread correctly.
  timestamp: 2026-03-26T00:07:00Z

- hypothesis: ZIP discovery failure causing empty location list
  evidence: discover_zip_codes('Austin, TX', 25) returns 64 ZIPs. uszipcode DB present at ~/.uszipcode/simple_db.sqlite (10MB). Works from both main and background threads.
  timestamp: 2026-03-26T00:05:00Z

- hypothesis: db.init_db() throws on first run
  evidence: init_db() runs successfully, creates DB at ~/.homesearch/homesearch.db.
  timestamp: 2026-03-26T00:04:00Z

## Resolution

root_cause: |
  Two compounding causes:
  1. Redfin provider always returns 403 Forbidden (stingray API blocked) - silently contributes zero listings, user gets no warning.
  2. _passes_filters() silently removes ALL listings when user selects criteria too restrictive for their area (e.g. price_max=100_000 in a market where all homes cost more). The "No properties found" message gives no indication of whether zero results came from no data vs. over-filtering.

  The immediate fix needed: when results are zero, show the user what filters are active and suggest broadening criteria. Also: surface Redfin 403 errors so user knows that provider is non-functional.

fix: |
  1. search_service.run_search(): added optional pre_filter_counts list parameter — appends count of deduped listings before client-side filtering.
  2. results.execute_search_with_spinner(): now returns tuple (list[Listing], int) with pre_filter_count. Passes pre_filter_counts to run_search().
  3. results.display_results(): added pre_filter_count=0 parameter. When results empty and pre_filter_count > 0, shows "X listings found before filtering" plus list of active filters. When pre_filter_count=0, shows "no data found" message.
  4. redfin_provider.py: catches 403/Forbidden specifically, prints "[Redfin] API access blocked (403)" once and breaks out of location loop instead of printing full traceback per ZIP.
  5. menu.py and saved_browser.py: updated to unpack (results, pre_filter_count) tuple from execute_search_with_spinner and pass pre_filter_count to display_results.

verification: |
  - run_search() with pre_filter_counts=[]: list populated with 69 (deduped count) for ZIP 10001 ✓
  - execute_search_with_spinner() returns (list, int) tuple: 36 results, pre_filter_count=36 for ZIP 78701 ✓
  - display_results([], criteria_with_filters, pre_filter_count=150): shows filter diagnostics ✓
  - display_results([], criteria, pre_filter_count=0): shows "no data found" message ✓
  - RedfinProvider.search() with ZIP 78701: prints "[Redfin] API access blocked (403)" once, no traceback spam ✓
  - saved_browser._run_search_now: importable, uses updated tuple unpacking ✓
  - All 5 integration tests pass ✓

files_changed:
  - homesearch/services/search_service.py
  - homesearch/tui/results.py
  - homesearch/providers/redfin_provider.py
  - homesearch/tui/menu.py
  - homesearch/tui/saved_browser.py
