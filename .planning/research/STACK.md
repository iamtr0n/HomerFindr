# Technology Stack

**Project:** HomerFindr — v1.1 Polish & Verification
**Researched:** 2026-03-25
**Scope:** Three specific v1.1 additions to an already-shipped v1.0 codebase: property card thumbnail photos, CLI progress bar polish, and menu wiring verification. Do NOT re-research the base stack.

---

## What Does NOT Change

The following v1.0 stack is validated and stable. No research needed, no changes recommended:

| Layer | Technology | Version |
|-------|-----------|---------|
| Python backend | FastAPI + Uvicorn | >=0.115.0 / >=0.30.0 |
| CLI framework | Typer + Rich | >=0.12.0 / >=13.7.0 |
| Arrow-key menus | questionary | >=2.1.1 |
| ASCII art | art | >=6.5 |
| Data scraping | homeharvest + redfin | >=0.4.0 / >=0.1.0 |
| Frontend | React 18 + Vite 5 + Tailwind 3 | as-pinned in package.json |
| UI components | shadcn/ui owned copies | in src/components/ui/ |
| Persistence | SQLite (stdlib sqlite3) | — |

---

## Feature 1: Property Card Thumbnail Photos

### Problem Diagnosis

Both providers already extract and populate `Listing.photo_url`. The field is mapped and populated in `homeharvest_provider.py` (lines 107, `primary_photo` / `img_src` columns) and in `redfin_provider.py` (lines 112-117). `PropertyCard.jsx` already renders `<img src={photo_url} ...>` with a fallback div (lines 28-42).

**The real issue is hotlink protection.** Realtor.com and Redfin both block browser `<img>` requests that originate from foreign domains (i.e., `localhost:8000` or any non-origin host). The `Referer` header sent by the browser does not match the source domain, so the CDN returns a 403 or redirects to a placeholder. This is why cards show "No Photo Available" even when `photo_url` is populated.

### Recommended Solution: FastAPI Image Proxy

Add a single FastAPI endpoint that fetches the remote image server-side (with correct headers and no cross-origin restriction) and streams it back to the browser.

**No new Python package is required.** `httpx>=0.27.0` is already in `pyproject.toml` and already used by dependencies. FastAPI's `StreamingResponse` is already available.

```
GET /api/proxy/image?url=<encoded_url>
→ FastAPI fetches url via httpx with browser-like headers
→ Streams response bytes back as image/jpeg or image/webp
```

**Frontend change:** `PropertyCard.jsx` replaces `src={photo_url}` with `src={photo_url ? \`/api/proxy/image?url=${encodeURIComponent(photo_url)}\` : ''}`. All other card logic stays the same.

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | >=0.27.0 (already installed) | Async HTTP client for proxy endpoint | Already in stack; supports async streaming, custom headers |
| FastAPI StreamingResponse | already in stack | Stream image bytes back to browser | Standard FastAPI pattern, no new import needed |

**Do not add a new image proxy library.** `httpx` + `StreamingResponse` is sufficient and already present.

**Do not add a React image caching library** (react-query-cache is already handling caching at the component level via TanStack Query).

### homeharvest Photo Field Names (MEDIUM confidence)

Based on code inspection of `homeharvest_provider.py` and PyPI/GitHub research:

- homeharvest DataFrame column is `primary_photo` (direct URL string) with `img_src` as a fallback column name depending on version
- The provider already handles both: `row.get("primary_photo", "") or row.get("img_src", "") or ""`
- redfin provider reads from `home_data.get("photos")` (list) or `staticMapUrl` (string fallback)
- Both map to `Listing.photo_url: str = ""`

**No provider code changes are needed for photo fetching.** The `photo_url` field is already populated when the scraper returns data. The gap is entirely in the browser display layer (hotlink blocking).

---

## Feature 2: CLI Progress Bars and Animation Polish

### Problem Diagnosis

`homesearch/tui/results.py` already has a manual spinner loop using `rich.live.Live` + a manual braille character array (lines 52-63). This works but is brittle (manual timing, manual character cycling). The v1.1 task is to replace or augment this with `rich.progress.Progress` for a more polished, idiomatic result.

**No new packages are needed.** `rich>=13.7.0` is already in `pyproject.toml` and includes the full `rich.progress` module with all required column types.

### Rich Progress API (HIGH confidence)

Rich 14.1.0 is the current stable release (2025). The following are confirmed available:

| Class | Module | Purpose |
|-------|--------|---------|
| `Progress` | `rich.progress` | Context manager; owns the Live display |
| `SpinnerColumn` | `rich.progress` | Animated spinner glyph (replaces manual braille loop) |
| `TextColumn` | `rich.progress` | Text label (provider name, "Searching...") |
| `BarColumn` | `rich.progress` | Visual fill bar (use only if total is known) |
| `TaskProgressColumn` | `rich.progress` | "N%" (use only if total is known) |
| `TimeElapsedColumn` | `rich.progress` | Elapsed seconds (useful for indeterminate search) |

**Indeterminate mode** (correct for search, total unknown):

```python
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[bold cyan]{task.description}"),
    TimeElapsedColumn(),
    console=console,
    transient=True,
) as progress:
    task = progress.add_task("Searching realtor...", total=None)
    # ... run search in thread ...
    progress.update(task, description="Searching redfin...")
```

`total=None` produces a pulsing indeterminate animation rather than a percentage bar — correct for scraping where result count is unknown upfront. `transient=True` removes the bar from output after completion, keeping results clean.

**Critical constraint (HIGH confidence):** Rich `Live` / `Progress` context managers must be fully exited before any `questionary` prompt is called. This is already respected in the existing `results.py` design (line 65 comment: "Live fully exited — safe for console.print and questionary"). The refactored version must maintain this invariant.

### What NOT to Add

- Do not add `tqdm` — Rich's Progress is already in stack and has richer terminal output
- Do not add `alive-progress` — same reason; redundant
- Do not add `yaspin` — same reason

---

## Feature 3: Settings / Saved Searches Menu Wiring Verification

### Finding: No New Stack Additions Needed

Code inspection of `homesearch/tui/menu.py` shows all four menu options are fully wired:

- `_handle_new_search()` → `wizard.run_search_wizard()` + `results.execute_search_with_spinner()` + `results.display_results()` — complete
- `_handle_saved_searches()` → `saved_browser.show_saved_searches_browser()` — complete; full CRUD (run, toggle, rename, delete) is implemented in `saved_browser.py`
- `_handle_settings()` → `settings.show_settings_menu()` — complete; Email, Search Defaults, About sub-pages all implemented in `settings.py`
- `_handle_web_ui()` → `web_launcher.start_server()` + `webbrowser.open()` — complete

**v1.1 task is end-to-end verification, not new wiring.** The handlers exist; the question is whether they work correctly at runtime (edge cases, config loading, first-run flow, etc.). No stack changes are implied.

---

## No New Dependencies for v1.1

**Zero new Python packages are required for v1.1.** All three features use capabilities already present:

| Capability Needed | Already In Stack As |
|-------------------|---------------------|
| Server-side image proxy | `httpx` (already in pyproject.toml) + FastAPI `StreamingResponse` |
| Rich progress bars | `rich>=13.7.0` (already installed), `rich.progress` module |
| Menu wiring verification | Existing TUI code in `homesearch/tui/` |

**Zero new frontend npm packages are required.** The `PropertyCard.jsx` photo URL change is a one-line `src=` attribute edit. No new React libraries needed.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Photo proxy | httpx (already installed) + FastAPI StreamingResponse | requests + new proxy library | requests is not in stack; adding a dedicated proxy library (anyio-http-proxy, etc.) is overkill for a single image endpoint |
| Photo proxy | Server-side FastAPI proxy | CORS header injection on photo URLs | The source domains (realtor.com CDN, redfin CDN) are third-party; we cannot modify their response headers |
| CLI progress | rich.progress.Progress (already installed) | tqdm, alive-progress, yaspin | All are redundant with Rich already in stack |
| Photo caching | Browser cache via proxy response headers (Cache-Control) | react-image or similar | Adding a React image library for a project that already uses TanStack Query for data management is unnecessary |

---

## Integration Notes

- `httpx.AsyncClient` is recommended over `httpx.Client` for the proxy endpoint since FastAPI routes are already async. Use `async with httpx.AsyncClient() as client:` inside the async route handler.
- The proxy endpoint should forward the `Accept` header from the incoming request and set `User-Agent` to a browser-like string to avoid the CDN blocking the server-side fetch.
- `StreamingResponse` from `fastapi.responses` streams bytes without buffering the full image in memory — important for large listing photos.
- `transient=True` on the `Progress` instance is critical; it ensures the progress bar disappears from terminal output after search completes and before the results table is printed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Photo URL fields already populated | HIGH | Confirmed by direct code inspection of both providers and Listing model |
| Hotlink protection as root cause | MEDIUM | Common CDN behavior confirmed by web research; specific CDN configs for realtor.com/redfin not officially documented |
| httpx proxy approach works | HIGH | Standard FastAPI + httpx pattern; StreamingResponse is stable API |
| Rich Progress API (SpinnerColumn, total=None) | HIGH | Confirmed from Rich 14.1.0 official docs; indeterminate mode via total=None is documented |
| Menu wiring completeness | HIGH | All four handlers confirmed by direct code inspection; implementations verified in wizard.py, saved_browser.py, settings.py, web_launcher.py |
| Zero new deps needed | HIGH | Confirmed by tracing all three features back to already-installed packages |

---

## Sources

- [Rich Progress Display docs — Rich 14.1.0](https://rich.readthedocs.io/en/latest/progress.html) — SpinnerColumn, TextColumn, indeterminate mode
- [Rich progress.py source — Textualize/rich](https://github.com/Textualize/rich/blob/master/rich/progress.py) — all column types confirmed present
- [HomeHarvest GitHub — Bunsly/HomeHarvest](https://github.com/Bunsly/HomeHarvest) — img_src field listed in property data schema
- [HomeHarvest PyPI](https://pypi.org/project/homeharvest/) — version and field documentation
- Codebase inspection: `homesearch/providers/homeharvest_provider.py` line 107, `redfin_provider.py` lines 112-117, `homesearch/tui/results.py`, `homesearch/tui/menu.py`, `frontend/src/components/PropertyCard.jsx`
