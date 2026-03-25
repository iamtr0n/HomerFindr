# Codebase Concerns

**Analysis Date:** 2026-03-25

---

## Security Considerations

**CORS Wildcard in Production API:**
- Risk: The FastAPI app allows all origins, methods, and headers with no restrictions.
- Files: `homesearch/api/routes.py` lines 20-25
- Current mitigation: None. `allow_origins=["*"]` is set unconditionally.
- Recommendations: Restrict origins to `http://localhost:*` in dev and the actual deployed domain in production. At minimum, check `settings.debug` or an env var before opening the wildcard.

**SMTP Password Stored in Plaintext .env:**
- Risk: SMTP credentials (including Gmail app password) live in a `.env` file. If the file is accidentally committed or the server is compromised, credentials are exposed.
- Files: `homesearch/config.py`, `.env.example`
- Current mitigation: `.env` is (presumably) gitignored.
- Recommendations: Document that `SMTP_PASSWORD` must never be the real account password — only a Gmail App Password or equivalent. Consider supporting secret manager injection for production deployments.

**No Authentication on Any API Endpoint:**
- Risk: Every API endpoint (`/api/searches`, `/api/report/send`, `/api/report/generate`) is publicly accessible with no authentication. The `/api/report/send` endpoint allows anyone to trigger outbound email from the configured SMTP account.
- Files: `homesearch/api/routes.py`
- Current mitigation: The server defaults to `127.0.0.1:8000`, limiting local exposure.
- Recommendations: Add at minimum a static bearer token check via middleware before deploying to any network-accessible host. The `send_report` endpoint is especially risky to leave open.

**SQL via Dynamic String Formatting in `update_search`:**
- Risk: `update_search` in `database.py` builds a `SET` clause by iterating `**kwargs` keys directly into an f-string: `f"{k} = ?"`. Any caller passing an unexpected key can inject arbitrary column names.
- Files: `homesearch/database.py` lines 162-180
- Current mitigation: Callers are internal Python code only; no user input reaches this path directly today.
- Recommendations: Add an explicit allowlist of permitted column names (`ALLOWED_UPDATE_FIELDS = {"criteria_json", "name", "is_active", "last_run_at"}`) and raise if any key is not in the set.

---

## Tech Debt

**`db.init_db()` Called Multiple Times on Every Search:**
- Issue: `run_search` calls `db.init_db()` at the top of every invocation, even though the API already calls `init_db()` at startup via the `@app.on_event("startup")` handler.
- Files: `homesearch/services/search_service.py` line 47, `homesearch/services/report_service.py` line 19, `homesearch/api/routes.py` line 30
- Impact: Minor overhead per request; `CREATE TABLE IF NOT EXISTS` is idempotent so no correctness issue, but the repeated calls are wasteful and signal unclear ownership of initialization.
- Fix approach: Remove `db.init_db()` from service functions. Make it the sole responsibility of the startup handler and the CLI entrypoints.

**`_safe_float` / `_safe_int` Duplicated Across Two Provider Files:**
- Issue: Identical helper functions are copy-pasted verbatim into both provider modules.
- Files: `homesearch/providers/homeharvest_provider.py` lines 169-182, `homesearch/providers/redfin_provider.py` lines 173-186
- Impact: Any bug fix must be applied twice; easy to diverge over time.
- Fix approach: Move both helpers to `homesearch/providers/base.py` or a new `homesearch/providers/utils.py` module and import from there.

**`sortedResults` Logic Duplicated Across Two Frontend Pages:**
- Issue: The sort function (price_asc, price_desc, sqft_desc, newest) is copy-pasted identically into both `NewSearch.jsx` and `SearchResults.jsx`.
- Files: `frontend/src/pages/NewSearch.jsx` lines 20-29, `frontend/src/pages/SearchResults.jsx` lines 35-44
- Impact: Sort behavior or sort options can diverge silently when one copy is updated.
- Fix approach: Extract to a shared `frontend/src/utils/sortListings.js` helper and import it in both pages.

**`on_event("startup")` Deprecated FastAPI Pattern:**
- Issue: `@app.on_event("startup")` is deprecated in FastAPI in favor of the `lifespan` context manager pattern.
- Files: `homesearch/api/routes.py` lines 28-30
- Impact: Will generate deprecation warnings in newer FastAPI versions and will be removed in a future major version.
- Fix approach: Replace with a `@asynccontextmanager` lifespan function passed to `FastAPI(lifespan=lifespan)`.

**`garage_spaces` Always `None` in HomeHarvest Provider:**
- Issue: `garage_spaces` is declared as a local variable and set to `None`, then the `parking_garage` field only sets `has_garage = True` — the spaces count is never extracted.
- Files: `homesearch/providers/homeharvest_provider.py` lines 111-116
- Impact: The `garage_spaces_min` filter in `_passes_filters` can never match against HomeHarvest data; users filtering by garage spaces get no results from Realtor.com.
- Fix approach: Attempt to parse `row.get("parking_garage")` as an integer for garage spaces when present.

**Stub Comment in `_passes_filters` Radius Check:**
- Issue: A `pass` statement with comment "Already filtered by ZIP code discovery" exists where radius filtering from lat/long should be applied.
- Files: `homesearch/services/search_service.py` lines 178-180
- Impact: Listings fetched by the Redfin provider (which searches by ZIP but returns properties from adjacent areas) are not radius-filtered. Results can include properties outside the intended radius.
- Fix approach: Implement the haversine check using `listing.latitude`/`listing.longitude` against the search center coordinates, or remove the dead code block entirely.

**`result_count` Field on `SavedSearch` Never Populated:**
- Issue: `SavedSearch.result_count: int = 0` is declared in the model but no database column exists for it and no code sets it.
- Files: `homesearch/models.py` line 103, `homesearch/database.py` (schema has no `result_count` column)
- Impact: The field always returns `0`, misleading any frontend code that might try to display a count without running the search.
- Fix approach: Either remove the field from the model, or add a `result_count` column that is updated after each run.

**`NewSearch.jsx` Handles `search_id` Response But Does Nothing With It:**
- Issue: `handleResults` checks `if (data.search_id)` with a comment "could navigate to results page" but takes no action.
- Files: `frontend/src/pages/NewSearch.jsx` lines 13-18
- Impact: After a "Save & Search" operation, the user stays on the new-search page instead of being redirected to the persisted results view, requiring a manual trip to the Dashboard.
- Fix approach: Add `navigate(`/search/${data.search_id}/results`)` inside the `if (data.search_id)` block.

---

## Performance Bottlenecks

**Synchronous Blocking HTTP Scraping on API Request Thread:**
- Problem: Both `HomeHarvestProvider.search()` and `RedfinProvider.search()` perform synchronous HTTP scraping (including explicit `time.sleep(1.5)` and `time.sleep(2)` calls) directly on the FastAPI request thread. A search over 50 ZIP codes takes 50 × 3.5 seconds = ~175 seconds minimum before results are returned.
- Files: `homesearch/providers/homeharvest_provider.py` lines 36-37, `homesearch/providers/redfin_provider.py` lines 28, 49
- Cause: Providers use synchronous libraries (`homeharvest`, `redfin`) with blocking sleep-based rate limiting called from a synchronous FastAPI route.
- Improvement path: Run provider calls in a `ThreadPoolExecutor` via `asyncio.run_in_executor`, or switch to async HTTP with proper rate limiting. At minimum, cap ZIP code batch sizes and return partial results with pagination.

**No Pagination on Search Results Endpoints:**
- Problem: All search result endpoints return every matching listing in a single response with no limit or offset.
- Files: `homesearch/api/routes.py` lines 47-51, 119-126
- Cause: No pagination parameters exist on any endpoint.
- Improvement path: Add `limit` and `offset` query parameters. The frontend already caps display at 50/card grid but still fetches all records.

**ZIP Code Discovery Runs on Every Preview Search:**
- Problem: The `resolve_zip_codes` call in `run_search` re-runs the full `uszipcode` spatial search on every preview, even when the user just clicked the "Find ZIPs" button in the frontend moments before.
- Files: `homesearch/services/search_service.py` lines 24-35, `homesearch/api/routes.py` line 50
- Cause: The frontend sends `zip_codes` populated from a prior `discoverZips` call, but the backend's `resolve_zip_codes` still fires when the location is set without zip_codes (e.g. first-time preview without clicking "Find ZIPs").
- Improvement path: Cache ZIP discovery results by (location, radius) for the session lifetime using a simple dict or Redis.

---

## Fragile Areas

**Redfin Provider Depends on Undocumented Internal API Shape:**
- Files: `homesearch/providers/redfin_provider.py`
- Why fragile: The `redfin` package wraps Redfin's internal "stingray" API. The nested response path `payload.exactMatch`, `payload.sections[0].rows[0]`, `homeData.addressInfo.centroid.centroid.latitude` is deeply nested and can silently break whenever Redfin changes its internal API contract.
- Safe modification: Wrap all dict accesses in the `_home_to_listing` method with `.get()` defensively (already partially done) and add null checks at each nesting level.
- Test coverage: None — no tests exist for any provider.

**HomeHarvest Provider Uses Column Name Guessing:**
- Files: `homesearch/providers/homeharvest_provider.py` lines 72-74, 97-107
- Why fragile: Column names are probed via a priority list (e.g., `row.get("street") or row.get("street_address")`, `row.get("list_price") or row.get("price") or row.get("sold_price")`). If `homeharvest` renames or adds columns, the silent fallback means data is silently dropped rather than an error being raised.
- Safe modification: Log a warning when both column name candidates are missing.
- Test coverage: None.

**Address-Based Deduplication is Fragile:**
- Files: `homesearch/services/search_service.py` lines 63-74, 92-99
- Why fragile: The dedup key is a normalized address string. The normalization only handles a fixed set of street suffix abbreviations. Listings with slightly different formatting (unit numbers, directional prefixes like "N" vs "North", abbreviation variants not in the list) will not deduplicate correctly and will appear as duplicates in results.
- Safe modification: Prefer deduplication by `(source, source_id)` first, then fall back to address normalization only when source IDs differ.
- Test coverage: None.

**Scheduler Uses Global State and Is Not Shut Down Cleanly:**
- Files: `homesearch/services/scheduler_service.py`
- Why fragile: `_scheduler` is a module-level global. If `start_scheduler` is called twice (e.g., in a hot-reload scenario during development), the guard `if _scheduler is not None: return` silently drops the second call. `stop_scheduler` is defined but never called — there is no shutdown hook registered in the FastAPI app.
- Safe modification: Register `stop_scheduler` via the FastAPI lifespan context manager to ensure clean shutdown. This also prevents the APScheduler background thread from outliving the process on Ctrl+C.
- Test coverage: None.

---

## Test Coverage Gaps

**Zero Test Files Exist:**
- What's not tested: The entire codebase. No unit tests, integration tests, or end-to-end tests were found.
- Files: All of `homesearch/` and `frontend/src/`
- Risk: Any change to provider parsing logic, filter logic, deduplication, or database operations can silently break without detection.
- Priority: High

**Critical Paths With No Coverage:**
- `_passes_filters` in `homesearch/services/search_service.py` — the core filter logic that determines what users see. Edge cases around `None` values (listings missing price, sqft, etc.) are especially risky.
- `upsert_listing` in `homesearch/database.py` — the update path only refreshes `price`, `photo_url`, and `source_url`; other changed fields (beds, sqft) are silently ignored on re-runs.
- `_normalize_address` in `homesearch/services/search_service.py` — dedup correctness depends entirely on this function.
- `build_html_report` in `homesearch/services/report_service.py` — HTML injection possible if `listing.address` or `listing.source_url` contains unescaped HTML/JS.

---

## Known Bugs

**`upsert_listing` Does Not Update Bedrooms, Bathrooms, or Square Footage:**
- Symptoms: If a listing's bedrooms or sqft changes on the source site (e.g., corrected listing data), the cached value in SQLite is never updated.
- Files: `homesearch/database.py` lines 203-209
- Trigger: Any re-run of a saved search after a listing was previously seen.
- Workaround: None currently — the only fields updated on re-seen listings are `price`, `photo_url`, `source_url`, and `last_seen_at`.

**`_passes_filters` Silently Passes Listings With Missing Data:**
- Symptoms: A user filtering for `price_max=500000` will still receive listings with `price=None` because the condition `listing.price and listing.price > criteria.price_max` short-circuits on `None`.
- Files: `homesearch/services/search_service.py` lines 125-126
- Trigger: Any search with a price filter, given that many listings from both providers have `price=None`.
- Workaround: None — the user must ignore null-price results manually.

**`api.previewSearch` Posts to Wrong URL:**
- Symptoms: The preview endpoint is defined at `/api/search/preview` (singular) but `api.js` calls `/search/preview` without the `/api` prefix properly... actually `BASE = '/api'` so it becomes `/api/search/preview`. However, the route is defined as `@app.post("/api/search/preview")` — this doubles the `/api` prefix when the FastAPI app is mounted at root, resulting in a 404.
- Files: `frontend/src/api.js` line 23, `homesearch/api/routes.py` line 47
- Trigger: Clicking the Search button on the New Search page without saving.
- Workaround: The "Save & Search" flow hits `/api/searches` which does work correctly.

---

## Dependencies at Risk

**`homeharvest` and `redfin` Packages Wrap Unofficial APIs:**
- Risk: Both packages scrape or call undocumented internal APIs of commercial real estate platforms (Realtor.com via `homeharvest`, Redfin via the `redfin` stingray API). Either platform can break these integrations at any time without notice and with no obligation to maintain backward compatibility.
- Impact: The entire data layer stops returning results with no error surfaced to the user (errors are caught and swallowed in `run_search`).
- Migration plan: Build provider-level health checks that return a status indicator. Consider adding a fallback data source (e.g., the `rapidapi_key` field in config already suggests Zillow via RapidAPI was planned but never implemented).

**`uszipcode` Uses a Bundled Offline SQLite Database:**
- Risk: The `uszipcode` package ships a static ZIP code database. ZIP codes change over time (new ZIPs added, boundaries shifted). The bundled data may be years out of date.
- Impact: ZIP discovery may miss newer ZIP codes or return stale city/population data.
- Migration plan: Periodically update the `uszipcode` package or supplement with a live geocoding API call.

**`apscheduler` 3.x Reached Maintenance-Only Status:**
- Risk: APScheduler 3.x is in maintenance mode; APScheduler 4.x has a significantly different API and is not backward compatible.
- Impact: Security fixes may stop being backported to the 3.x branch.
- Migration plan: Plan migration to APScheduler 4.x or switch to a simpler alternative (e.g., `rocketry`, `celery beat`, or a system-level cron job calling `homesearch report`).

---

## Missing Critical Features

**No Error Feedback in Frontend Search:**
- Problem: `handleSearch` in `SearchForm.jsx` catches errors with `console.error` only. The user sees nothing if the search fails (timeout, provider error, server down).
- Blocks: Users cannot know whether a long wait is normal or an error occurred.
- Files: `frontend/src/components/SearchForm.jsx` lines 115-117

**No Way to Edit a Saved Search:**
- Problem: The `PUT /api/searches/{search_id}` endpoint exists in the backend but no frontend UI exposes it. Users must delete and recreate searches to change criteria.
- Blocks: Basic workflow for refining searches over time.
- Files: `homesearch/api/routes.py` lines 83-93 (backend exists), `frontend/src/pages/Dashboard.jsx` (no edit button)

**Report Triggered Silently Even When SMTP Is Not Configured:**
- Problem: The `/api/report/send` endpoint returns `{"sent": false}` when SMTP is unconfigured, but the frontend `Dashboard.jsx` shows "Report sent!" on any successful HTTP 200 response, regardless of the `sent` field value.
- Files: `homesearch/services/report_service.py` lines 137-139, `frontend/src/pages/Dashboard.jsx` lines 131-135

---

*Concerns audit: 2026-03-25*
