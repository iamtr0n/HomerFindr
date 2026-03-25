# Codebase Structure

**Analysis Date:** 2026-03-25

## Directory Layout

```
HomerFindr/                         # Project root
├── homesearch/                     # Python package — backend + CLI
│   ├── __init__.py
│   ├── main.py                     # CLI entry point (Typer app)
│   ├── config.py                   # Settings via pydantic-settings
│   ├── models.py                   # Shared Pydantic models
│   ├── database.py                 # SQLite access layer (no ORM)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py               # FastAPI app + all REST endpoints
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseProvider ABC
│   │   ├── homeharvest_provider.py # Realtor.com / MLS via homeharvest
│   │   └── redfin_provider.py      # Redfin via redfin package
│   └── services/
│       ├── __init__.py
│       ├── search_service.py       # Fan-out, dedup, filter, persist
│       ├── zip_service.py          # ZIP code discovery (uszipcode)
│       ├── report_service.py       # Report generation + SMTP
│       └── scheduler_service.py    # APScheduler daily job
├── frontend/                       # React SPA — web dashboard
│   ├── index.html                  # Vite HTML entrypoint
│   ├── package.json
│   ├── vite.config.js              # Vite config; dev proxy /api → :8000
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx                # React mount + QueryClientProvider
│       ├── App.jsx                 # BrowserRouter, Nav, top-level Routes
│       ├── api.js                  # All fetch calls to /api/*
│       ├── index.css               # Tailwind directives
│       ├── components/
│       │   ├── PropertyCard.jsx    # Single listing card
│       │   └── SearchForm.jsx      # Full search criteria form
│       └── pages/
│           ├── Dashboard.jsx       # Saved searches list + run/delete
│           ├── NewSearch.jsx       # Create + preview a new search
│           └── SearchResults.jsx   # Results for a saved search
├── pyproject.toml                  # Python package manifest + deps
├── .env.example                    # Required env vars template
├── .gitignore
└── README.md
```

## Directory Purposes

**`homesearch/`:**
- Purpose: Installable Python package; both CLI and web server live here
- Contains: Entry point, config, models, database, API, providers, services
- Key files: `main.py` (CLI), `api/routes.py` (FastAPI), `models.py` (data contracts)

**`homesearch/api/`:**
- Purpose: FastAPI application and REST route definitions
- Contains: Single `routes.py` with all endpoints; also mounts `frontend/dist` as static files
- Key files: `homesearch/api/routes.py`

**`homesearch/providers/`:**
- Purpose: Pluggable data source adapters — one file per external platform
- Contains: `BaseProvider` ABC + concrete implementations
- Key files: `homesearch/providers/base.py`, `homesearch/providers/homeharvest_provider.py`, `homesearch/providers/redfin_provider.py`

**`homesearch/services/`:**
- Purpose: Business logic orchestration; no HTTP or CLI concerns
- Contains: Search fan-out, ZIP discovery, report generation, scheduler
- Key files: `homesearch/services/search_service.py`

**`frontend/src/components/`:**
- Purpose: Reusable React components
- Contains: `PropertyCard.jsx` (renders a single `Listing`), `SearchForm.jsx` (full criteria form with ZIP discovery)

**`frontend/src/pages/`:**
- Purpose: Route-level page components, one per React Router route
- Contains: `Dashboard.jsx` (`/`), `NewSearch.jsx` (`/search/new`), `SearchResults.jsx` (`/search/:id/results`)

**`frontend/dist/`** (generated, not committed):
- Purpose: Vite production build output; served as static files by FastAPI
- Generated: Yes (`npm run build`)
- Committed: No

## Key File Locations

**Entry Points:**
- `homesearch/main.py`: CLI entry point; `app` Typer instance referenced by `pyproject.toml`
- `homesearch/api/routes.py`: FastAPI `app` instance; launched via `uvicorn.run()` from `main.py:serve()`
- `frontend/src/main.jsx`: React SPA mount point

**Configuration:**
- `homesearch/config.py`: All settings (`Settings` class); import `settings` singleton
- `.env.example`: Documents required env vars (SMTP, database path, RapidAPI key)
- `frontend/vite.config.js`: Dev server proxy (`/api` → `http://127.0.0.1:8000`)
- `pyproject.toml`: Python deps, package name, entry point script

**Core Logic:**
- `homesearch/models.py`: All Pydantic models — the shared contract for the entire system
- `homesearch/database.py`: All SQLite operations; schema DDL inline as `SCHEMA` string
- `homesearch/services/search_service.py`: `run_search()` — the central search orchestrator
- `frontend/src/api.js`: All frontend API calls; single `api` export object

**Providers:**
- `homesearch/providers/base.py`: `BaseProvider` ABC — implement this to add a new data source
- `homesearch/providers/homeharvest_provider.py`: Realtor.com adapter
- `homesearch/providers/redfin_provider.py`: Redfin adapter

## Naming Conventions

**Python Files:**
- `snake_case.py` for all modules
- `*_provider.py` suffix for data source adapters in `providers/`
- `*_service.py` suffix for service layer modules in `services/`

**Python Classes:**
- `PascalCase` — e.g., `HomeHarvestProvider`, `SearchCriteria`, `SavedSearch`
- Provider classes: `<Platform>Provider` — e.g., `RedfinProvider`

**Python Functions:**
- `snake_case` — e.g., `run_search`, `discover_zip_codes`, `upsert_listing`
- Private helpers prefixed with `_` — e.g., `_normalize_address`, `_passes_filters`, `_row_to_listing`

**Frontend Files:**
- `PascalCase.jsx` for components and pages — e.g., `PropertyCard.jsx`, `Dashboard.jsx`
- `camelCase.js` for non-component modules — e.g., `api.js`

**Frontend Components:**
- Default export matches filename — `export default function PropertyCard()`

## Where to Add New Code

**New Data Source Provider:**
1. Create `homesearch/providers/<platform>_provider.py` implementing `BaseProvider`
2. Add required `name` property and `search(criteria) -> list[Listing]` method
3. Register the new provider instance in `homesearch/services/search_service.py:get_providers()`
4. If provider requires an API key, add the key to `homesearch/config.py:Settings` and `.env.example`

**New API Endpoint:**
- Add route to `homesearch/api/routes.py`
- Define request/response Pydantic models inline in `routes.py` (current pattern) or in `models.py` if reused

**New CLI Command:**
- Add `@app.command()` function to `homesearch/main.py`
- For sub-commands: create a new `Typer()` instance and `app.add_typer()` (as done with `saved_app`)

**New Service:**
- Create `homesearch/services/<name>_service.py`
- Import into `api/routes.py` or `main.py` as needed; avoid circular imports by using local imports

**New Frontend Page:**
- Create `frontend/src/pages/<PageName>.jsx`
- Add route in `frontend/src/App.jsx` under `<Routes>`
- Add navigation link to `Nav` component in `App.jsx` if needed

**New Frontend Component:**
- Create `frontend/src/components/<ComponentName>.jsx`
- Use TanStack Query (`useQuery`, `useMutation`) for any server data; call through `api.js`

**New Config Setting:**
- Add field to `Settings` class in `homesearch/config.py`
- Document in `.env.example`

## Special Directories

**`frontend/dist/`:**
- Purpose: Vite production build output — JS/CSS bundles + `index.html`
- Generated: Yes, via `cd frontend && npm run build`
- Committed: No
- Note: FastAPI conditionally mounts this directory; if it does not exist, the web UI is unavailable

**`.planning/codebase/`:**
- Purpose: GSD architecture and planning documents
- Generated: By GSD tooling
- Committed: Yes

**`~/.homesearch/`** (outside repo, at runtime):
- Purpose: Default SQLite database location (`homesearch.db`)
- Location: Configured via `database_path` in `Settings`; defaults to `Path.home() / ".homesearch" / "homesearch.db"`
- Generated: Yes, on first `db.init_db()` call
- Committed: No

---

*Structure analysis: 2026-03-25*
