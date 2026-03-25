# Architecture

**Analysis Date:** 2026-03-25

## Pattern Overview

**Overall:** Monorepo with a Python backend (FastAPI + CLI) and a separate React SPA frontend. The backend follows a layered provider/service pattern — external data sources are abstracted behind a plugin interface, and a service layer orchestrates search fan-out, deduplication, persistence, and reporting.

**Key Characteristics:**
- Provider pattern: all real estate data sources implement `BaseProvider` and are registered in `search_service.py`
- Dual interface: the same Python package exposes both a Typer CLI and a FastAPI HTTP server
- Frontend is a pre-built static SPA served directly from FastAPI via `StaticFiles`; in dev, Vite proxies `/api` to the backend
- Persistence is SQLite via raw `sqlite3` (no ORM); the database module is a plain function library (`database.py`)
- Pydantic models are the shared data contract used by CLI, API, providers, and database layer

## Layers

**Models Layer:**
- Purpose: Define shared data shapes used everywhere
- Location: `homesearch/models.py`
- Contains: `SearchCriteria`, `Listing`, `SavedSearch`, `ZipInfo`, `ListingType`, `PropertyType` enums
- Depends on: Pydantic only
- Used by: All other layers

**Configuration Layer:**
- Purpose: Load typed settings from environment / `.env`
- Location: `homesearch/config.py`
- Contains: `Settings` (pydantic-settings `BaseSettings`), singleton `settings`
- Depends on: `pydantic-settings`
- Used by: `database.py`, `scheduler_service.py`, `report_service.py`, `main.py`

**Database Layer:**
- Purpose: All SQLite read/write operations; no ORM
- Location: `homesearch/database.py`
- Contains: Schema DDL, connection factory, CRUD functions for saved searches, listings, search results linkage
- Depends on: `config.py`, `models.py`, `sqlite3`
- Used by: `search_service.py`, `report_service.py`, `api/routes.py`, `main.py`

**Provider Layer:**
- Purpose: Fetch raw listings from an external data source and normalize them to `Listing`
- Location: `homesearch/providers/`
- Contains: `BaseProvider` (ABC), `HomeHarvestProvider` (Realtor.com/MLS via `homeharvest`), `RedfinProvider` (Redfin via `redfin`)
- Depends on: `models.py`, third-party scraping libraries
- Used by: `search_service.py` only

**Service Layer:**
- Purpose: Orchestrate business logic; does not own HTTP or CLI concerns
- Location: `homesearch/services/`
- Contains:
  - `search_service.py` — fan-out to providers, dedup, client-side filtering, persistence
  - `zip_service.py` — offline ZIP code discovery via `uszipcode`
  - `report_service.py` — run all active searches, detect new listings, build HTML, send SMTP email
  - `scheduler_service.py` — APScheduler background job wiring
- Depends on: `models.py`, `database.py`, `providers/`, `config.py`
- Used by: `api/routes.py`, `main.py`

**API Layer:**
- Purpose: FastAPI REST endpoints consumed by the React frontend; also serves the built SPA
- Location: `homesearch/api/routes.py`
- Contains: FastAPI `app` instance, request/response models, all `/api/*` routes, static file mount
- Depends on: `services/`, `database.py`, `models.py`
- Used by: Frontend, and by `main.py` (`serve` command) via `uvicorn.run`

**CLI Layer:**
- Purpose: Typer CLI for interactive wizard, server launch, saved search management, report dispatch
- Location: `homesearch/main.py`
- Contains: `app` Typer instance, `search` / `serve` / `report` commands, `saved` sub-commands
- Depends on: `services/`, `database.py`, `models.py`, `config.py`
- Used by: Package entry point `homesearch = "homesearch.main:app"` in `pyproject.toml`

**Frontend Layer:**
- Purpose: React SPA for web-based search, results browsing, and report triggering
- Location: `frontend/`
- Contains: Vite + React 18, TanStack Query for data fetching, React Router v6 pages, Tailwind CSS
- Depends on: Backend `/api/*` endpoints via `frontend/src/api.js`
- Used by: End users; served as static files from FastAPI in production

## Data Flow

**New Search (CLI path):**
1. User runs `homesearch search` → `main.py:search_interactive()` collects `SearchCriteria` interactively
2. `zip_service.discover_zip_codes()` resolves location to a list of ZIP codes (offline, `uszipcode`)
3. `search_service.run_search(criteria)` fans out to all enabled providers in parallel-sequential loop
4. Each provider fetches from its external source, maps results to `Listing` objects
5. `search_service` deduplicates by normalized address, scores quality (prefers MLS/realtor source), applies client-side filters
6. If `search_id` is set, listings are upserted in SQLite, linked to the search, and flagged new/existing
7. Results displayed in terminal via Rich table

**New Search (Web/API path):**
1. Frontend `POST /api/searches` with `SearchRequest` JSON body
2. `api/routes.py:create_and_run_search()` saves the search to SQLite, calls `search_service.run_search()`
3. Same fan-out → dedup → filter → persist flow as CLI
4. Returns `SearchResponse` with full `Listing` list; React renders `PropertyCard` components

**Daily Report:**
1. APScheduler fires `daily_report_job` at configured hour (default 07:00)
2. `report_service.generate_report()` marks all existing results `is_new=0`, re-runs each active saved search
3. New listings (those not seen before) are identified and collected
4. `report_service.build_html_report()` renders an HTML email
5. `report_service.send_email_report()` delivers via SMTP (Gmail/Outlook compatible)

**State Management (Frontend):**
- TanStack Query (`@tanstack/react-query`) manages all server state (fetching, caching, invalidation)
- No client-side global state store; component-local `useState` for form state
- `frontend/src/api.js` is the single fetch abstraction (plain `fetch`, no SDK)

## Key Abstractions

**BaseProvider:**
- Purpose: Plugin interface that all data source adapters must implement
- Examples: `homesearch/providers/base.py`, `homesearch/providers/homeharvest_provider.py`, `homesearch/providers/redfin_provider.py`
- Pattern: Abstract class with required `search(criteria) -> list[Listing]` and `name` property; optional `enabled` property for disabling without removal

**SearchCriteria:**
- Purpose: Single Pydantic model carrying all search parameters between CLI, API, providers, and database
- Examples: `homesearch/models.py:SearchCriteria`
- Pattern: All fields optional; criteria is serialized as JSON into `saved_searches.criteria_json` column

**Listing:**
- Purpose: Normalized property record — every provider maps its raw output to this shape
- Examples: `homesearch/models.py:Listing`
- Pattern: Source-agnostic; carries `source` and `source_id` fields for provenance tracking and deduplication

**SavedSearch:**
- Purpose: Persisted search profile — links a user-named search to its criteria and run history
- Examples: `homesearch/models.py:SavedSearch`
- Pattern: Stored with `criteria_json` (JSON-serialized `SearchCriteria`), `last_run_at` timestamp, `is_active` flag for report scheduling

## Entry Points

**CLI Entry Point:**
- Location: `homesearch/main.py` — `app` Typer instance
- Triggers: `homesearch` command via `pyproject.toml` script entry `homesearch.main:app`
- Responsibilities: Interactive search wizard, `serve` (launches uvicorn), `report`, `saved` subcommands

**FastAPI App:**
- Location: `homesearch/api/routes.py` — `app` FastAPI instance
- Triggers: `uvicorn.run("homesearch.api.routes:app", ...)` called from `main.py:serve()`
- Responsibilities: All `/api/*` REST endpoints, serving built frontend SPA from `frontend/dist/`

**Frontend Entry:**
- Location: `frontend/src/main.jsx`
- Triggers: Browser load of `index.html`
- Responsibilities: Mount React app, wrap with `QueryClientProvider` and `BrowserRouter`

## Error Handling

**Strategy:** Defensive per-provider isolation — individual provider failures print a message and continue; the search still returns results from other providers.

**Patterns:**
- Provider `search()` methods wrap their entire body in `try/except`, log via `print`, return empty list on failure
- `_row_to_listing()` in providers catches per-row exceptions individually, returns `None` and skips bad rows
- FastAPI routes raise `HTTPException(404)` for missing resources; no global error handler is defined
- CLI commands use Rich console output with color-coded error messages; no exceptions bubble to user

## Cross-Cutting Concerns

**Logging:** `print()` statements throughout backend; no structured logging framework. Prefixed with `[ServiceName]` convention (e.g., `[HomeHarvest]`, `[Scheduler]`, `[Report]`).

**Validation:** Pydantic v2 used for all model validation at API boundaries and database deserialization (`model_validate_json`, `model_dump_json`).

**Authentication:** None. The API has `CORSMiddleware` with `allow_origins=["*"]`. Intended for local/personal use only.

**Rate Limiting:** `HomeHarvestProvider` enforces a 1.5-second sleep between ZIP code queries to be respectful to Realtor.com.

**Database Initialization:** `db.init_db()` is called defensively at multiple entry points (CLI commands, FastAPI startup event, `run_search`). It is idempotent (`CREATE TABLE IF NOT EXISTS`).

---

*Architecture analysis: 2026-03-25*
