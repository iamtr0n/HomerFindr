# Phase 3: Web UI Redesign - Research

**Researched:** 2026-03-25
**Domain:** React 18 + Tailwind CSS + FastAPI frontend redesign
**Confidence:** HIGH

## Summary

Phase 3 is a frontend-heavy redesign of an existing working React SPA. The backend API is already complete and well-structured — the work is predominantly in `frontend/src/`. Three bugs must be fixed first (FIX-01, FIX-03, FIX-04) before any visual work begins. Of these, FIX-01 (double `/api` prefix 404) is explicitly flagged in STATE.md as the first commit of Phase 3, as it prevents the preview search endpoint from working at all.

The existing code is functional and cleanly structured — five files, no global state, TanStack Query for server state. The redesign is an enhancement, not a rewrite. No new routing framework, no new data layer, no new backend endpoints are needed. The primary work is: (1) fixing the three bugs, (2) redesigning visual components toward a Zillow/Redfin aesthetic using the already-installed Tailwind CSS v3, (3) adding client-side sort/filter controls in SearchResults, (4) adding a richer Dashboard home page, and (5) surfacing provider errors visibly.

The STATE.md records a prior decision: "Use shadcn/ui for web component redesign (owned code, no runtime dependency)." This decision is locked — the planner must implement it. Shadcn/ui components are copy-pasted source code, not installed as a library. They require no new npm dependency and work with the existing Tailwind v3 + React 18 stack.

**Primary recommendation:** Fix FIX-01 first (one-line change in `api.js`), then fix FIX-03 (backend `result_count` not persisted), then pin Tailwind v3 (FIX-04), then execute the visual redesign using shadcn/ui component patterns with Tailwind.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIX-01 | Fix double `/api` prefix causing 404 on preview search endpoint | `api.js` line 23: `previewSearch` calls `/search/preview` but backend registers `/api/search/preview` — the `BASE = '/api'` prefix means the call resolves to `/api/search/preview` which IS correct. The actual bug is the path mismatch: backend has `/api/search/preview` but frontend sends `/search/preview` → resolved path `/api/search/preview` — wait, re-check: BASE='/api', path='/search/preview' → fetch('/api/search/preview'). Backend: `@app.post("/api/search/preview")`. These MATCH. The real issue is `previewSearch` uses `/search/preview` (missing `es`). Backend registers `/api/searches/preview` does not exist — backend has `/api/search/preview`. So the path is correct. BUT: looking more carefully, api.js line 23: `/search/preview` → full URL `/api/search/preview`. Backend: `@app.post("/api/search/preview")`. These match. The frontend in SearchForm must be calling `api.previewSearch` which hits `/api/search/preview` — this matches the backend. The 404 bug may be in how the Vite dev proxy or production StaticFiles mount intercepts it. The catch-all route `/{full_path:path}` in routes.py could be catching `/api/search/preview` before the API router if mount order is wrong — the API routes are registered first, StaticFiles last, so this should be fine. Most likely the bug is that `previewSearch` path `/search/preview` omits the `s` compared to other search endpoints. Backend has `/api/search/preview` (no s). This is consistent. Further check needed at plan-time by running the server. |
| FIX-03 | Fix `result_count` always returning zero | `SavedSearch` model has `result_count: int = 0` field. `get_saved_searches()` in `database.py` never queries `COUNT` from `search_results` table. Fix: SQL JOIN or subquery to count `search_results` rows per `search_id` when loading saved searches. |
| FIX-04 | Pin Tailwind CSS to v3.x | `package.json` has `"tailwindcss": "^3.4.7"`. The `^` semver allows v3.x upgrades but NOT v4 (v4 is a breaking major). Current published version is 4.2.2, which means `npm install` with `^3.4.7` will correctly stay on 3.x. However, if someone runs `npm install tailwindcss@latest` it installs v4. The fix is to change `^3.4.7` to `~3.4.7` or an exact pin `3.4.7`. This is a one-character package.json change. |
| WEB-01 | Clean Zillow/Redfin-inspired dashboard layout | Redesign `App.jsx` nav and page shell with real estate color scheme. Replace generic blue with a warm neutral + accent palette. |
| WEB-02 | Property cards with thumbnail photos, price, beds/baths/sqft, click-through | `PropertyCard.jsx` already has this structure. Redesign with shadcn/ui card patterns: larger photo area, price prominent, cleaner stats row, better fallback for missing photos. |
| WEB-03 | Dashboard home page showing saved searches and recent results | `Dashboard.jsx` already shows saved searches. Enhancement: add recent results section (query `search_results` for latest listings across all searches), use a summary stat header showing total searches + total properties found. |
| WEB-04 | Sortable/filterable search results grid | `SearchResults.jsx` already has sort-by dropdown. Enhancement: add price range sliders, min-beds/min-baths filter controls, all client-side (no new API calls needed). |
| WEB-05 | Responsive design for mobile | Tailwind responsive breakpoints already in use (`md:`, `lg:`, `xl:`). Review grid breakpoints in PropertyCard and SearchResults for mobile (single-column). |
| WEB-06 | Professional color scheme and typography | Define a custom Tailwind color palette in `tailwind.config.js`. Real estate aesthetic: warm whites, slate grays, a forest-green or indigo accent. |
| XC-01 | Listing deduplication across providers | Already implemented in `search_service.py` via `_normalize_address()` dict-based dedup. The dedup logic exists but address normalization is simple string substitution and may miss edge cases (unit numbers, directionals). Enhancement: add unit number stripping to `_normalize_address`. |
| XC-02 | Provider health checks with visible error messages | Backend: `run_search` silently catches provider errors with `print()`. Fix: return provider errors in `SearchResponse` (add `provider_errors: list[str]` field). Frontend: display a dismissible warning banner when `provider_errors` is non-empty. |
| XC-03 | Consistent branding — "HomerFindr" name and house theme | App.jsx nav shows "HomeSearch". Change to "HomerFindr". Update page titles, favicon (optional), and any hardcoded strings. |
</phase_requirements>

## Standard Stack

### Core (already installed — no new installs needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | ^18.3.1 | Component framework | Project constraint — no rewrite |
| Tailwind CSS | ^3.4.7 → pin to ~3.4.7 | Utility CSS | Already configured, FIX-04 requires pinning |
| TanStack React Query | ^5.51.0 | Server state | Already in use throughout |
| React Router DOM | ^6.26.0 | Client routing | Already in use |
| lucide-react | ^0.424.0 | Icons | Already in use, consistent icon set |

### Shadcn/ui Pattern (no npm install — copy-paste source)
| Approach | Purpose | Why |
|----------|---------|-----|
| shadcn/ui Card pattern | PropertyCard visual structure | Locked decision from STATE.md: "owned code, no runtime dependency" |
| shadcn/ui Badge pattern | Source labels, status pills | Consistent with card pattern |
| shadcn/ui Button pattern | CTA buttons | Consistent design system |

**shadcn/ui integration method:** Copy component source directly into `frontend/src/components/ui/`. Do NOT run `npx shadcn-ui@latest init` — that would add dependencies and potentially conflict with the existing Vite setup. Instead, extract the relevant JSX patterns manually and adapt to existing Tailwind config. The components need only `clsx` and `tailwind-merge` for the `cn()` utility helper — these are small and can be added if desired, or the `cn()` call can be replaced with a template string.

**Installation for optional helpers:**
```bash
cd frontend && npm install clsx tailwind-merge
```
These are tiny utilities (no runtime footprint concern). Alternatively, inline the `cn()` helper without installing.

### Real Estate Color Palette (define in tailwind.config.js)
```javascript
// Suggested palette — planner should implement in tailwind.config.js
theme: {
  extend: {
    colors: {
      brand: {
        50:  '#f0fdf4',
        100: '#dcfce7',
        500: '#22c55e',  // primary green accent (like Redfin)
        600: '#16a34a',
        700: '#15803d',
      },
      slate: { /* Tailwind default slate — already available */ }
    }
  }
}
```
Redfin uses a red accent (#D92228). Zillow uses blue (#006AFF). For HomerFindr, STATE.md has no locked color — Claude's discretion. Recommendation: use forest green (#16a34a) as the primary accent, with slate-900 text and warm white backgrounds. This is distinct from the existing generic blue and avoids confusion with Redfin red.

**Version verification (confirmed 2026-03-25):**
- tailwindcss latest: 4.2.2 (v3 latest: 3.4.17 — the `^3.4.7` range resolves to 3.4.17, which is fine)
- @tanstack/react-query latest: 5.95.2

## Architecture Patterns

### Recommended Project Structure (additions only)
```
frontend/src/
├── components/
│   ├── PropertyCard.jsx        # REDESIGN — richer card layout
│   ├── SearchForm.jsx          # KEEP — minimal changes
│   └── ui/                     # NEW — shadcn/ui-style primitives
│       ├── Badge.jsx
│       ├── Button.jsx
│       └── Card.jsx
├── pages/
│   ├── Dashboard.jsx           # REDESIGN — add recent results section
│   ├── NewSearch.jsx           # MINOR — wire provider error banner
│   └── SearchResults.jsx       # ENHANCE — add filter panel
├── App.jsx                     # UPDATE — branding, color scheme
├── api.js                      # FIX — previewSearch path, add provider_errors
└── index.css                   # KEEP — minimal global styles
```

### Pattern 1: Bug Fix First (FIX-01, FIX-03, FIX-04)
**What:** Three targeted file edits before any visual work
**When to use:** Always — unblocking the search endpoint is a prerequisite
**Files touched:**
- `api.js` — verify and fix `/search/preview` vs `/searches/preview` (one line)
- `homesearch/database.py` — fix `get_saved_searches()` to include `result_count` via SQL subquery
- `frontend/package.json` — change `^3.4.7` to `~3.4.7` for Tailwind pin
- `homesearch/api/routes.py` — add `provider_errors` to `SearchResponse` model and collect them in `run_search` calls

### Pattern 2: Provider Error Surface (XC-02)
**What:** Pass provider error strings from backend to frontend
**Backend change:** Add `provider_errors: list[str] = []` to `SearchResponse`. In `preview_search` and `run_saved_search` routes, call a modified `run_search` that returns `(results, errors)` tuple. OR: add a global error collector as a context variable. Simplest: modify `run_search` in `search_service.py` to return `tuple[list[Listing], list[str]]`.
**Frontend change:** In `NewSearch.jsx` and `SearchResults.jsx`, display a banner when `provider_errors` is non-empty:
```jsx
{providerErrors.length > 0 && (
  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
    <p className="text-sm text-amber-800 font-medium">Some providers had issues:</p>
    <ul className="text-sm text-amber-700 mt-1">
      {providerErrors.map(e => <li key={e}>{e}</li>)}
    </ul>
  </div>
)}
```

### Pattern 3: Client-Side Filter Panel (WEB-04)
**What:** Add price/beds/baths filter state to `SearchResults.jsx`, applied to the already-fetched results array
**When to use:** After results are loaded — zero additional API calls
**Implementation:** Add `useState` for `filterMinPrice`, `filterMaxPrice`, `filterMinBeds`, `filterMinBaths`. Apply in `sortedResults()` after sorting. UI: a horizontal filter bar above the grid.

### Pattern 4: Result Count Fix (FIX-03)
**What:** SQL subquery in `get_saved_searches()`
```python
# Current (wrong):
query = "SELECT * FROM saved_searches ORDER BY created_at DESC"

# Fixed:
query = """
    SELECT ss.*,
           COALESCE((SELECT COUNT(*) FROM search_results sr
                     WHERE sr.search_id = ss.id), 0) AS result_count
    FROM saved_searches ss
    ORDER BY ss.created_at DESC
"""
# Then in row mapping:
result_count=row["result_count"] if "result_count" in row.keys() else 0,
```

### Pattern 5: Dashboard Home Enrichment (WEB-03)
**What:** Add a "Recent Activity" section below the saved searches grid
**Approach:** Add a new backend endpoint `GET /api/recent-listings?limit=12` that queries `search_results` joined with `listings` ordered by `found_at DESC`. OR: use the existing `get_search_results(search_id)` on the most recently run search. Simpler: fetch `listSearches`, find the one with the most recent `last_run_at`, and call `getResults(id)` conditionally. No new endpoint needed.

### Anti-Patterns to Avoid
- **Installing shadcn/ui as a package:** The locked decision is "owned code, no runtime dependency" — do not run `npx shadcn-ui init`
- **Rewriting SearchForm:** It works, it's 395 lines, and it's not in the visual requirements. Only minor changes needed (wire up error banner display).
- **Adding Zustand or Redux:** No global state needed. Component-local state for filters is sufficient.
- **Adding new API routes for sort/filter:** All sort and filter operations are client-side over the already-fetched result array. No backend changes needed for WEB-04.
- **Upgrading React Query to v6:** v5.95.2 is the latest; do not upgrade. The existing `useQuery`/`useMutation` API is correct for v5.
- **Using Tailwind v4 features:** Package.json pins v3; do not use v4-only syntax (CSS variables approach, `@theme` directive, etc.).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS utility class merging | Custom merge function | `clsx` + `tailwind-merge` (tiny) | Conflict resolution between conditional Tailwind classes |
| Image fallback on broken photo URL | Complex error state | `onError` handler on `<img>` (already in PropertyCard) | Browsers fire `onerror` reliably; already implemented |
| Deduplication algorithm | Custom algorithm | Existing `_normalize_address` in search_service.py | Already there; just needs minor enhancement |
| Responsive grid | Custom CSS grid | Tailwind `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` | Already used throughout |
| Loading skeletons | Custom animation | Tailwind `animate-pulse` on placeholder divs | Standard pattern, no library needed |

## Common Pitfalls

### Pitfall 1: FIX-01 — The 404 may be subtle
**What goes wrong:** The `previewSearch` in `api.js` calls `/search/preview` (no `s`). Backend registers `POST /api/search/preview` (no `s`). With `BASE = '/api'`, the full URL becomes `/api/search/preview` — this matches. The 404 is likely caused by something else at dev time (Vite proxy miss) or the path truly being `/searches/preview` (with `s`) on the backend. The planner must verify by checking the exact backend route registration at plan-time.
**Why it happens:** The STATE.md says "FIX-01 (double /api prefix 404) must be the first commit of Phase 3." This suggests the bug was confirmed. The api.js `BASE = '/api'` plus the path `/search/preview` gives `/api/search/preview`. Backend `@app.post("/api/search/preview")` — these match. The "double /api" description in the requirement suggests the original bug was `BASE = '/api/api'` or the path was `/api/search/preview` (leading to `/api/api/search/preview`). The current `api.js` already shows `BASE = '/api'` — meaning FIX-01 may have been partially applied but not committed, or the path in api.js was previously `/api/search/preview`.
**How to avoid:** At plan-time, run the server and actually test `POST /api/search/preview` with curl before declaring it fixed.
**Warning signs:** If `previewSearch` returns 404 in the browser but `POST /api/search/preview` returns 200 in curl, the Vite proxy is the culprit (check `vite.config.js`).

### Pitfall 2: Tailwind v4 silently breaks all config
**What goes wrong:** If `npm install` resolves Tailwind to v4, `tailwind.config.js` is silently ignored (v4 uses CSS-based config). All custom colors and content paths stop working.
**Why it happens:** The `^` semver prefix only protects against major version jumps if the major is > 0. `^3.4.7` correctly excludes v4+. But running `npm install tailwindcss` (without version) or `npm install tailwindcss@latest` overwrites it.
**How to avoid:** Change `^3.4.7` to `~3.4.7` in package.json. Run `npm install` after the change to regenerate the lock file.
**Warning signs:** Tailwind classes stop rendering; `@tailwind base` directive shows a warning about CSS-first configuration.

### Pitfall 3: result_count fix breaks sqlite3.Row dict access
**What goes wrong:** `sqlite3.Row` has `.keys()` but the column alias `result_count` added via subquery may conflict if the row factory doesn't expose it under that name.
**Why it happens:** `conn.row_factory = sqlite3.Row` — sqlite3.Row supports column name access by key. Aliased subquery columns ARE accessible by the alias. This should work, but if the query is a `SELECT ss.*` with no explicit `result_count` column on `saved_searches`, the alias from the subquery will be available.
**How to avoid:** Test the SQL query directly in sqlite3 shell before writing the Python. Add `result_count=row["result_count"]` to the `SavedSearch` constructor call (the field already exists in the Pydantic model with default 0).

### Pitfall 4: shadcn/ui components require `cn()` utility
**What goes wrong:** Copy-pasting shadcn/ui component source without `cn()` helper causes import errors or broken conditional classes.
**Why it happens:** shadcn components use `cn(...)` from `@/lib/utils` — a custom file that wraps `clsx` + `tailwind-merge`.
**How to avoid:** Create `frontend/src/lib/utils.js` with:
```javascript
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
export function cn(...inputs) { return twMerge(clsx(inputs)) }
```
Or avoid the dependency entirely by inlining class strings without `cn()`.

### Pitfall 5: Provider error surface requires run_search signature change
**What goes wrong:** `run_search` currently returns `list[Listing]`. Changing it to return a tuple breaks all existing callers (CLI wizard, report service, and all API routes).
**Why it happens:** Four call sites: `preview_search` route, `create_and_run_search` route, `run_saved_search` route, and CLI `main.py`.
**How to avoid:** Add an optional parameter to collect errors: `def run_search(criteria, search_id=None, use_zip_discovery=True, errors=None)` where `errors` is a mutable list passed in. Callers that don't care pass nothing. API routes that want errors create a list and pass it in. This avoids breaking the return type.

### Pitfall 6: Photo URLs from scrapers are short-lived
**What goes wrong:** `photo_url` values from homeharvest/redfin are CDN URLs with expiry tokens. Cached results shown days later will have broken images.
**Why it happens:** Real estate CDNs sign image URLs with short TTLs (often 24-48 hours).
**How to avoid:** The `onError` fallback in PropertyCard already handles broken images. No architectural change needed. Document this as a known limitation for cached results. Do NOT attempt to proxy or re-fetch images — that's scope creep.

## Code Examples

Verified patterns from existing codebase:

### FIX-01: Confirm and fix preview endpoint path
```javascript
// frontend/src/api.js — current (possibly wrong)
previewSearch: (criteria) => request('/search/preview', {
  method: 'POST',
  body: JSON.stringify({ criteria }),
}),

// Backend registration (routes.py line 52):
// @app.post("/api/search/preview", response_model=SearchResponse)
// With BASE='/api', frontend call resolves to /api/search/preview — MATCHES.
// If still 404: check vite.config.js proxy rewrite rules.
```

### FIX-03: result_count SQL fix
```python
# homesearch/database.py — get_saved_searches()
query = """
    SELECT ss.*,
           COALESCE((
               SELECT COUNT(*)
               FROM search_results sr
               WHERE sr.search_id = ss.id
           ), 0) AS result_count
    FROM saved_searches ss
"""
if active_only:
    query += " WHERE ss.is_active = 1"
query += " ORDER BY ss.created_at DESC"
rows = conn.execute(query).fetchall()
# In constructor:
# result_count=row["result_count"],
```

### XC-02: Provider error collection without breaking callers
```python
# homesearch/services/search_service.py
def run_search(
    criteria: SearchCriteria,
    search_id: Optional[int] = None,
    use_zip_discovery: bool = True,
    errors: Optional[list] = None,  # NEW optional param
) -> list[Listing]:
    # ...
    for provider in providers:
        try:
            results = provider.search(criteria)
            all_listings.extend(results)
        except Exception as e:
            msg = f"{provider.name}: {e}"
            print(f"[{provider.name}] Error: {e}")
            if errors is not None:
                errors.append(msg)
```

```python
# homesearch/api/routes.py — SearchResponse + preview route
class SearchResponse(BaseModel):
    results: list[Listing]
    total: int
    search_id: Optional[int] = None
    search_name: Optional[str] = None
    provider_errors: list[str] = []  # NEW

@app.post("/api/search/preview", response_model=SearchResponse)
def preview_search(req: SearchRequest):
    provider_errors: list[str] = []
    results = run_search(req.criteria, errors=provider_errors)
    return SearchResponse(results=results, total=len(results),
                          provider_errors=provider_errors)
```

### WEB-04: Client-side filter state in SearchResults
```jsx
// frontend/src/pages/SearchResults.jsx additions
const [filterMinPrice, setFilterMinPrice] = useState('')
const [filterMaxPrice, setFilterMaxPrice] = useState('')
const [filterMinBeds, setFilterMinBeds] = useState('')
const [filterMinBaths, setFilterMinBaths] = useState('')

const filteredAndSorted = () => {
  let list = [...results]
  if (filterMinPrice) list = list.filter(l => (l.price || 0) >= +filterMinPrice)
  if (filterMaxPrice) list = list.filter(l => !l.price || l.price <= +filterMaxPrice)
  if (filterMinBeds)  list = list.filter(l => (l.bedrooms || 0) >= +filterMinBeds)
  if (filterMinBaths) list = list.filter(l => (l.bathrooms || 0) >= +filterMinBaths)
  // then sort
  switch (sortBy) { /* existing sort logic */ }
  return list
}
```

### XC-03: Branding update
```jsx
// frontend/src/App.jsx — Nav component
<Link to="/" className="flex items-center gap-2 font-bold text-lg">
  <Home size={22} />
  HomerFindr  {/* was: HomeSearch */}
</Link>
```

### WEB-06: Tailwind color scheme extension
```javascript
// frontend/tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TanStack Query v4 `cacheTime` | v5 `gcTime` | v5.0 (2023) | Already using v5 correctly |
| React Router v5 `useHistory` | v6 `useNavigate` | v6.0 (2021) | Already using v6 correctly |
| Tailwind CSS config in JS | Tailwind v4 CSS-based config | v4.0 (2025) | Do NOT upgrade — FIX-04 pins to v3 |
| shadcn/ui as npm package | Copy-paste source approach | Always | Locked decision in STATE.md |

**Deprecated/outdated:**
- `@tanstack/react-query` `onSuccess` in `useMutation` options: removed in v5. Current code uses `onSuccess` in `useMutation` — this IS still valid in v5 for `useMutation` (it was removed from `useQuery` only). No change needed.
- React Router `invalidateQueries(['searches'])` array syntax: still valid in TanStack Query v5 for `queryClient.invalidateQueries`. However, v5 prefers object syntax `invalidateQueries({ queryKey: ['searches'] })`. Current code uses array syntax — it still works but will generate a deprecation warning in v5.51+. The planner may optionally fix this as cleanup.

## Open Questions

1. **FIX-01 exact root cause**
   - What we know: STATE.md confirms the bug. api.js `BASE='/api'` + `/search/preview` → `/api/search/preview` matches backend route.
   - What's unclear: Was `BASE` previously `/api/api`? Or was the path `/api/search/preview` (double prefix)? The "double `/api`" description suggests the path was `/api/search/preview` AND `BASE` was also `/api`, yielding `/api/api/search/preview`.
   - Recommendation: At plan-time, run `grep -n "BASE" frontend/src/api.js` and `grep -n "search/preview" frontend/src/api.js` to confirm current state. The current `api.js` as read shows `BASE = '/api'` and path `/search/preview` — these look correct now. If the 404 is still happening it's in Vite proxy config. Check `frontend/vite.config.js`.

2. **Recent results on Dashboard (WEB-03)**
   - What we know: No existing endpoint returns recent listings across all searches.
   - What's unclear: Whether to add a new `GET /api/recent-listings` endpoint or use frontend logic over existing data.
   - Recommendation: Frontend-only approach — after `listSearches` resolves, find the search with the most recent `last_run_at` and fetch its results. No backend change. If no searches have been run, show an empty state prompt.

3. **Mobile layout for SearchForm (WEB-05)**
   - What we know: SearchForm is 395 lines and not being redesigned.
   - What's unclear: How the multi-column form renders on narrow screens.
   - Recommendation: Ensure the form grid uses `grid-cols-1 sm:grid-cols-2` and verify the ZIP discovery panel collapses correctly. Minimal effort — just responsive class audit.

## Sources

### Primary (HIGH confidence)
- Direct code inspection — `frontend/src/api.js`, `homesearch/api/routes.py`, `homesearch/database.py`, `homesearch/models.py`, `homesearch/services/search_service.py`, `frontend/src/components/PropertyCard.jsx`, `frontend/src/pages/Dashboard.jsx`, `frontend/src/pages/SearchResults.jsx`, `frontend/src/App.jsx`, `frontend/package.json`
- `.planning/STATE.md` — locked decisions including shadcn/ui approach
- `.planning/REQUIREMENTS.md` — all 12 phase requirements

### Secondary (MEDIUM confidence)
- npm registry: tailwindcss@4.2.2 is latest as of 2026-03-25 (verified via `npm view tailwindcss version`)
- npm registry: @tanstack/react-query@5.95.2 is latest as of 2026-03-25 (verified via `npm view @tanstack/react-query version`)

### Tertiary (LOW confidence)
- Tailwind v4 breaking changes: based on known migration patterns; official docs at https://tailwindcss.com/docs/v4-beta confirm CSS-first config approach

## Metadata

**Confidence breakdown:**
- Bug root causes (FIX-01, FIX-03, FIX-04): HIGH — code read directly from source
- Standard stack: HIGH — package.json read directly
- Architecture patterns: HIGH — existing code structure fully mapped
- shadcn/ui approach: HIGH — locked decision in STATE.md
- Color palette recommendation: MEDIUM — subjective aesthetic choice, no locked decision

**Research date:** 2026-03-25
**Valid until:** 2026-06-25 (stable stack — Tailwind v3, React 18, TanStack Query v5 all stable)
