# Feature Landscape

**Domain:** Local CLI + web dashboard real estate aggregator — v1.1 Polish & Verification
**Researched:** 2026-03-25
**Overall confidence:** HIGH (all three v1.1 features verified against installed package source)

---

## Context: What's Already Built (v1.0, Out of Scope)

All of the following are confirmed working in v1.0 and are NOT rebuild targets:

- Arrow-key CLI with 15-field wizard, ASCII art splash, main menu (Search / Saved Searches / Settings / Launch Web UI / Exit)
- Web dashboard with shadcn/ui property cards, sortable/filterable results, stat header, provider error banners
- Provider architecture (homeharvest + Redfin), SQLite saved searches, FastAPI REST API
- Email reports, SMTP wizard, first-run setup, `pipx install .` → `homerfindr` global command, macOS `.command` launcher

The v1.1 feature set is narrow and additive: photos, CLI progress polish, Settings/Saved Searches wiring verification, and end-to-end install verification.

---

## Table Stakes

Features that must work correctly for v1.1 to be considered shipped.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Property card thumbnail photos appearing in web dashboard | Real estate cards without photos look like a broken prototype; every reference site (Zillow, Redfin) shows a photo thumbnail as the primary visual element | Low | Infrastructure fully in place — `Listing.photo_url`, SQLite `photo_url` column, `<img src={photo_url}>` in `PropertyCard.jsx` all exist. Gap is verifying providers reliably populate the field end-to-end |
| CLI search progress shows per-provider / per-ZIP granularity | Multi-ZIP searches take 30–90+ seconds with the current spinner showing only "Searching realtor..."; no sense of how far along the search is — reads as potentially frozen | Medium | Existing `execute_search_with_spinner` uses `Rich.Live + Text`; needs upgrade to `Rich.Progress` with `add_task` + `advance` per ZIP. Threading model stays the same |
| Settings sub-menus navigate without exceptions | Settings and Saved Searches are in the main menu; if any sub-action raises an unhandled error or navigates to a dead end, the core UX loop breaks | Low | `menu.py` dispatches correctly to `settings.py` and `saved_browser.py`; the gap is verification + patching any runtime edge cases (empty SMTP config KeyError, delete not refreshing the list, etc.) |
| Saved Searches "Run Now" executes a search and updates last_run_at | Users who save a search expect to re-run it; if "Run Now" silently fails or doesn't persist the timestamp, the feature is broken in practice | Low | `_run_search_now()` in `saved_browser.py` calls `execute_search_with_spinner` and `db.update_search`; needs verification that it completes without exception on a real search |
| Clean install works end-to-end on a fresh terminal session | The primary distribution method is `pipx install .` → `homerfindr`; if first-time setup fails or any main menu path crashes, the tool can't be shared with friends/family | Low | Not a build task — a verification task; requires walking every menu path on a clean install |

---

## Differentiators

Features that distinguish v1.1 from a simple bug-fix release.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-ZIP progress bar with task description | "Searching realtor.com [ZIP 3/7]..." transforms a 60-second wait into a visible, trust-building sequence. Users know the app is working, not frozen | Medium | `Rich.Progress.add_task(description, total=N)` + `advance()` from worker thread. `total` is known after `resolve_zip_codes()` runs. The `Progress` class (confirmed in installed `rich/progress.py`) supports multi-task display and thread-safe `advance()` calls |
| Styled "No Photo" placeholder (house icon, not grey rectangle) | A grey `h-52 bg-slate-100` div with "No Photo Available" text looks like a layout bug; a styled placeholder with a house icon looks intentional | Low | Pure React/CSS in `PropertyCard.jsx`. The fallback div already exists — needs an icon (lucide-react `Home` icon is already a project dependency) and a subtitle |
| Transient progress bar (clears on completion) | Bar disappearing when search completes keeps the terminal clean and lets the results table print without scrolling past progress UI | Low | `Progress(transient=True)` — single parameter |
| End-to-end verification checklist as a living artifact | A documented, runnable step-by-step checklist becomes the acceptance criterion for every future release; transforms "feels done" into "verified done" | Low | Not app code — a `.planning/` checklist file. Covers install, every CLI menu path, web UI paths, data paths, photo verification |

---

## Anti-Features

Features to explicitly NOT build in v1.1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Proxy / cache photos through the FastAPI backend | Adds latency, complexity, potential Realtor.com/Redfin ToS issues, and a file cache to maintain. Realtor.com CDN URLs work fine in browser direct-fetch | Use direct `photo_url` values as returned by providers; rely on `onError` fallback in `PropertyCard.jsx` for the inevitable dead links |
| Alt photos gallery / carousel | `homeharvest` returns `alt_photos: list[HttpUrl]` and the `Listing` model has room for it, but a gallery carousel is a v2 feature that adds significant React complexity for marginal v1.1 value | Store `primary_photo` only for now; `alt_photos` field exists and is documented for future use |
| Photo caching / local persistence | Requires mime-type detection, file store management, cache invalidation, and size limits. Browser caches externally fetched images naturally | Browser handles caching automatically; no app-level photo storage needed |
| Automated pytest suite for scraper paths | Writing reliable tests around live scrapers that rate-limit and change APIs is a separate project measured in days, not hours | Manual verification checklist covers the same acceptance surface for v1.1 |
| New search criteria fields or provider changes | Adding fields or providers touches the schema, providers, API, and frontend simultaneously — out of scope for a polish milestone | Defer to v1.2 |
| Rich progress bars in the web dashboard | Web has its own loading state via TanStack Query's `isLoading`; duplicating progress feedback in the Python API layer adds noise for no user benefit | Web spinner/skeleton stays as-is |

---

## Feature Dependencies

```
Photo pipeline (end-to-end verification):
  homeharvest `description.primary_photo` (HttpUrl field in Description model)
    → process_result() converts to string in `primary_photo` DataFrame column
    → homeharvest_provider.py row.get("primary_photo") → Listing.photo_url
    → SQLite listings.photo_url TEXT column
    → GET /api/search → JSON Listing serialization
    → PropertyCard.jsx <img src={photo_url}> with onError fallback

  Key verification step: run a real search and confirm at least some Listing
  records in SQLite have non-empty photo_url values, and those URLs render
  in the browser (no 403). This is the only remaining gap — the code is correct.

  Redfin photos: provider reads home_data.get("photos") list, falls back to
  home_data.get("staticMapUrl") string (a satellite/street map thumbnail).
  staticMapUrl is reliably populated → Redfin cards will almost always have a photo.

CLI progress upgrade dependencies:
  resolve_zip_codes() must complete first → total ZIP count known → Progress total set
  Provider ZIP-level loop must call on_zip_done callback → Progress.advance() called
  Live context must close before questionary prompts → same constraint as existing spinner

  Minimal invasive path:
    add `on_zip_done: Callable | None = None` parameter to run_search()
    provider loops call on_zip_done() after each ZIP if provided
    execute_search_with_spinner() creates Progress, passes callback via closure

Settings/Saved Searches wiring:
  menu.py _handle_settings() → settings.show_settings_menu() [confirmed dispatches]
  menu.py _handle_saved_searches() → saved_browser.show_saved_searches_browser() [confirmed]
  Both modules exist and implement expected sub-menus.
  The dependency is runtime verification on a real run, not new code.
```

---

## Photo URL: Evidence-Backed Analysis

**Confidence: HIGH** — verified from installed package source at
`.venv/lib/python3.11/site-packages/homeharvest/`

The homeharvest `Description` model (`models.py` line 116):
```python
primary_photo: HttpUrl | None = None
alt_photos: list[HttpUrl] | None = None
```

`utils.py` `ordered_properties` (lines 73-74): `"primary_photo"` and `"alt_photos"` are both in the output DataFrame column list.

`utils.py` `process_result()` (line 136):
```python
prop_data["primary_photo"] = str(description.primary_photo) if description.primary_photo else None
```

The homeharvest provider in this project reads `row.get("primary_photo", "")` — correct column name.

The `img_src` fallback in the provider (`row.get("img_src", "")`) is dead code — homeharvest does not produce an `img_src` column. It doesn't hurt, but a better fallback would be `alt_photos` (parse the comma-separated string from the DataFrame). That's a low-risk one-line improvement.

**The photo pipeline is complete.** The only thing to verify is whether Realtor.com's API actually returns a primary photo for listings in a given search area (it usually does for active listings; may be empty for SOLD or off-market listings).

---

## CLI Progress: Evidence-Backed Analysis

**Confidence: HIGH** — verified from installed Rich source at
`.venv/lib/python3.11/site-packages/rich/progress.py`

Current implementation (`tui/results.py`): `Live + Text + threading.Event` spinner.
Works, but is purely qualitative — no indication of how many ZIPs remain.

Rich `Progress` APIs confirmed available:
- `Progress(transient=True)` — bar clears on exit
- `Progress.add_task(description, total=N)` — creates a labeled task bar
- `Progress.advance(task_id, advance=1)` — thread-safe increment
- Can be used as a context manager: `with Progress(...) as progress:`

The upgrade pattern:
```python
# In execute_search_with_spinner, after resolve_zip_codes:
with Progress(
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    MofNCompleteColumn(),
    TimeRemainingColumn(),
    transient=True,
    console=console,
) as progress:
    task = progress.add_task("Searching...", total=len(zip_codes))
    # Pass progress.advance callback into run_search
```

This is a localized change to `execute_search_with_spinner` and a small addition to `run_search` / the provider loop. No changes to models, API, or database.

---

## Verification: What End-to-End Covers for This App

**Confidence: MEDIUM** — synthesized from codebase inspection and domain knowledge.

For a local-only CLI+web app, end-to-end verification means confirming every user-visible path completes without exceptions and produces expected output. There is no external infrastructure, no cloud, no auth — all paths terminate locally.

**Install path:**
- `pip install -e .` completes → `homerfindr` command available on PATH
- `cd frontend && npm install && npm run build` → `frontend/dist/` exists

**CLI paths (every main menu branch):**
- Launch → splash → first-run wizard (if no config) → main menu appears
- New Search → full 15-field wizard navigable by arrows only → spinner → results table → URL selection → save prompt → return to menu
- Saved Searches → list renders → Run Now (triggers real search, updates last_run_at) → Toggle (flips is_active) → Rename → Delete (with confirm)
- Settings → Email Settings → Configure SMTP → Manage Recipients (add + remove) → Search Defaults (all 5 fields: city, state, radius, listing type, price range) → About page
- Launch Web UI → server starts → browser opens → web dashboard loads → return to CLI menu still works
- Exit → server shuts down cleanly → terminal returns to shell

**Web UI paths:**
- Dashboard loads: saved searches list populates, stat counts accurate
- New Search form: all field types submit → results page shows listings with photos (or fallback)
- Source badge, price, beds/baths/sqft stats, year built visible on cards
- Sort and filter controls change the displayed results
- Provider error banner appears when a provider returns an error
- "View on [source]" links open the correct external URL

**Data verification:**
- After a CLI search, SQLite `listings` table contains rows with non-empty `photo_url` for at least some entries
- After a web search, same verification
- Saved search `last_run_at` updates correctly after "Run Now"

**Specific v1.1 verification items:**
- `photo_url` non-empty for at least 50% of realtor listings in a real search
- Redfin listings have `photo_url` (staticMapUrl fallback ensures near-100%)
- Photos render in browser (no universal 403 pattern from Realtor.com CDN)
- Progress bar shows ZIP count during CLI search
- Settings sub-menus don't crash on empty/default config (no KeyError on missing SMTP keys)
- Delete from Saved Searches refreshes the list without requiring restart

---

## MVP Recommendation for v1.1

This is a polish and verification milestone. The frame is: verify what's built, fix what's broken, polish what's rough.

**Priority order:**

1. **Verify photo pipeline end-to-end** — run a real search, inspect SQLite, confirm photos render in web UI. If `primary_photo` is empty, add the `alt_photos` fallback to the homeharvest provider (one-line fix). Redfin photos should work via `staticMapUrl` without any changes.

2. **Polish "No Photo" placeholder** — swap the grey `bg-slate-100` div for a styled `Home` icon + "No Photo Available" subtitle. Already in `PropertyCard.jsx`, takes 10 minutes.

3. **Upgrade CLI progress to per-ZIP bar** — swap `Live + Text` for `Progress + add_task` + callback in `execute_search_with_spinner`. Add `on_zip_done` callback parameter to `run_search`. High UX payoff for ~30 lines of changes across two files.

4. **Verify Settings/Saved Searches wiring** — walk every sub-menu path. Fix any runtime edge cases found (empty config KeyError, list not refreshing after delete). The code already dispatches correctly.

5. **Document and run the full verification checklist** — walk all paths on a clean terminal session. This is the acceptance criterion for "v1.1 shipped."

**Defer to v2.0:** Alt photos gallery, photo proxy/caching, automated test suite, new providers, new search fields.

---

## Sources

- `/Users/iamtron/Documents/GitHub/HomerFindr/.venv/lib/python3.11/site-packages/homeharvest/utils.py` — `ordered_properties` confirms `"primary_photo"` column name; `process_result()` confirms extraction logic (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/.venv/lib/python3.11/site-packages/homeharvest/core/scrapers/models.py` — `Description.primary_photo: HttpUrl | None` and `alt_photos: list[HttpUrl] | None` confirmed (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/.venv/lib/python3.11/site-packages/rich/progress.py` — `Progress`, `track()`, `add_task()`, `advance()`, `transient` parameter confirmed available in installed version (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/homesearch/providers/homeharvest_provider.py` — current photo extraction reads `row.get("primary_photo", "")` correctly; `img_src` fallback is dead code (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/homesearch/providers/redfin_provider.py` — `home_data.get("photos")` list + `staticMapUrl` fallback; reliable photo coverage (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/homesearch/tui/results.py` — existing `execute_search_with_spinner` uses `Live + Text`; upgrade path identified (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/homesearch/tui/menu.py` — confirmed correct dispatch to `settings.py` and `saved_browser.py` (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/homesearch/models.py` — `Listing.photo_url: str = ""` confirmed (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/homesearch/database.py` — `photo_url TEXT DEFAULT ''` in SQLite schema confirmed (HIGH confidence, direct source)
- `/Users/iamtron/Documents/GitHub/HomerFindr/frontend/src/components/PropertyCard.jsx` — `<img src={photo_url}>` with `onError` fallback div confirmed (HIGH confidence, direct source)
- [Rich Progress Display Documentation](https://rich.readthedocs.io/en/latest/progress.html) — `track()`, `Progress`, spinner patterns (MEDIUM confidence — WebSearch verified, not directly fetched)
