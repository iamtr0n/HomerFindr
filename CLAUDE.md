<!-- GSD:project-start source:PROJECT.md -->
## Project

**HomerFindr**

A polished home search aggregator that pulls listings from multiple platforms (Realtor.com, Redfin, and more) into one place. It has two equally important interfaces: a fun, colorful CLI with arrow-key navigation and ASCII art, and a clean Zillow/Redfin-inspired web dashboard. Built for personal use and sharing with friends/family who are house hunting.

**Core Value:** Find homes fast across all platforms without juggling multiple websites — zero typing required in the CLI, just arrows and Enter.

### Constraints

- **Stack**: Keep existing Python + React stack — no rewrites
- **Data sources**: Only free providers (homeharvest, redfin packages) — no paid APIs
- **Local-first**: Everything runs on the user's machine, no cloud dependencies
- **Zero typing**: Search wizard must be navigable entirely with arrows + Enter
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11+ - Backend, CLI, API server, data providers, scheduling
- JavaScript (ES Modules) - Frontend React application
- JSX - React component templates (`frontend/src/**/*.jsx`)
- HTML - Single-page app shell (`frontend/index.html`)
## Runtime
- Python 3.11+ (required by `pyproject.toml`: `requires-python = ">=3.11"`)
- Node.js (version not pinned; used only for frontend build tooling)
- Python: `pip` with `setuptools>=68.0` build backend (`pyproject.toml`)
- Node: `npm` (`frontend/package.json`)
- Lockfiles: No `requirements.txt` lockfile; no `package-lock.json` detected (not committed)
## Frameworks
- FastAPI `>=0.115.0` - REST API server (`homesearch/api/routes.py`)
- Uvicorn `>=0.30.0` (standard extras) - ASGI server, launched via `uvicorn.run()` in `homesearch/main.py`
- React `^18.3.1` - UI component framework (`frontend/src/`)
- React Router DOM `^6.26.0` - Client-side routing
- TanStack React Query `^5.51.0` - Server state and async data fetching
- Vite `^5.4.0` - Dev server and build tool (`frontend/vite.config.js`)
- Typer `>=0.12.0` - CLI framework (`homesearch/main.py`)
- Rich `>=13.7.0` - Terminal output formatting, tables, prompts
- pytest `>=8.0` (dev dependency)
- pytest-asyncio `>=0.23` (dev dependency)
- `@vitejs/plugin-react` `^4.3.1` - Vite plugin for React/JSX transform
- PostCSS `^8.4.40` - CSS processing pipeline
- Autoprefixer `^10.4.19` - CSS vendor prefixes
## Key Dependencies
- `homeharvest>=0.4.0` - Scrapes Realtor.com (MLS) listings; no API key required (`homesearch/providers/homeharvest_provider.py`)
- `redfin>=0.2.0` - Accesses Redfin stingray API; no API key required (`homesearch/providers/redfin_provider.py`)
- `pydantic>=2.7.0` - Data models and validation (`homesearch/models.py`)
- `pydantic-settings>=2.3.0` - Settings management from env/`.env` file (`homesearch/config.py`)
- `pandas>=2.2.0` - Used to process homeharvest DataFrame results
- `apscheduler>=3.10.0` - Background cron scheduler for daily email reports (`homesearch/services/scheduler_service.py`)
- `uszipcode>=1.0.1` - Offline ZIP code database for radius discovery (`homesearch/services/zip_service.py`)
- `geopy>=2.4.0` - Geospatial utilities (imported as dependency, available for distance calculations)
- `httpx>=0.27.0` - Async HTTP client (available; used internally by dependencies)
- `aiofiles>=24.1.0` - Async file operations
- `jinja2>=3.1.0` - HTML templating (available; email report uses inline string building currently)
- `python-multipart>=0.0.9` - Required by FastAPI for form data
- `lucide-react` `^0.424.0` - Icon library for React UI
- Tailwind CSS `^3.4.7` - Utility-first CSS framework (`frontend/tailwind.config.js`)
## Configuration
- Settings loaded from `.env` file via `pydantic-settings` (`homesearch/config.py`)
- `.env.example` present at project root
- Key env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `REPORT_EMAIL`, `RAPIDAPI_KEY`, `HOST`, `PORT`, `REPORT_HOUR`, `REPORT_MINUTE`, `DATABASE_PATH`
- Defaults: SQLite at `~/.homesearch/homesearch.db`, server on `127.0.0.1:8000`, report at 07:00
- `frontend/vite.config.js` - Vite build config; dev server proxies `/api` to `http://127.0.0.1:8000`
- `frontend/tailwind.config.js` - Tailwind scans `./index.html` and `./src/**/*.{js,jsx}`
- `frontend/postcss.config.js` - PostCSS config (Tailwind + Autoprefixer)
- `pyproject.toml` - Python package metadata and dependencies
## Platform Requirements
- Python 3.11+
- Node.js (any modern LTS; used for `npm install && npm run build`)
- Install Python package: `pip install -e .`
- Install frontend: `cd frontend && npm install`
- Self-hosted: runs as a single process (`homesearch serve`) on the local machine
- No containerization or cloud deployment config detected
- Frontend must be pre-built (`npm run build`) before serving; FastAPI serves the `frontend/dist/` directory as static files
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- `snake_case` for all module names: `search_service.py`, `zip_service.py`, `report_service.py`
- `snake_case` for package directories: `homesearch/`, `homesearch/providers/`, `homesearch/services/`
- Private helpers prefixed with `_`: `_safe_float`, `_safe_int`, `_row_to_listing`, `_normalize_address`, `_passes_filters`
- `PascalCase` for all classes: `BaseProvider`, `HomeHarvestProvider`, `RedfinProvider`, `SearchCriteria`, `SavedSearch`
- `PascalCase` for Pydantic models: `Settings`, `ZipInfo`, `Listing`
- `snake_case` for all functions and methods: `run_search`, `discover_zip_codes`, `get_saved_searches`
- CLI command functions use short imperative names: `search`, `serve`, `report`, `saved_list`, `saved_run`
- Helper functions in modules prefixed with `_`: `_parse_city`, `_parse_state`, `_listing_html`
- `snake_case` throughout: `all_listings`, `zip_codes`, `listing_type`, `property_types`
- Module-level constants in `UPPER_SNAKE_CASE`: `SCHEMA`, `_LISTING_TYPE_MAP`
- Short loop variables acceptable for iterations: `l` for listing, `s` for search, `z` for zip
- `PascalCase` for component files and component functions: `SearchForm.jsx`, `PropertyCard.jsx`, `Dashboard.jsx`
- `camelCase` for utilities: `api.js`
- Page components in `src/pages/`, reusable components in `src/components/`
- `camelCase` for variables and functions: `zipResults`, `zipLoading`, `discoverZips`, `toggleZipExclude`
- `UPPER_SNAKE_CASE` for module-level constant arrays: `LISTING_TYPES`, `PROPERTY_TYPES`, `TRISTATE`
- `camelCase` for event handlers: `handleSearch`, `set`, `setNum`
## Code Style
- No formatter config file detected (no `.prettierrc`, `biome.json`, or `.eslintrc`)
- Python: PEP 8 style, 4-space indentation
- JavaScript/JSX: 2-space indentation, single quotes for imports, template literals for string interpolation
- Trailing commas used in multi-line Python and JS structures
- No ESLint or Prettier config detected in the project
- No `ruff`, `black`, or `flake8` config in `pyproject.toml`
- Code relies on developer discipline — no enforced tooling
## Import Organization
- Module-level imports preferred; lazy imports inside functions used for optional dependencies:
- `from homesearch import database as db` aliased consistently across all modules
- Type imports via `from typing import Optional` (not `typing.Optional`)
- `from __future__ import annotations` used in `homesearch/models.py` for forward references
- None configured. All imports use relative paths: `'../api'`, `'../pages/Dashboard'`
## Error Handling
- Providers wrap entire search logic in `try/except Exception` and call `traceback.print_exc()` then `continue`:
- Per-location errors inside loops use `continue` to skip failing ZIPs, not abort entire search
- Optional dependency missing: caught with `ImportError`, prints install hint, returns empty list
- `run_search` in `homesearch/services/search_service.py` catches per-provider errors and logs with `print(f"[{provider.name}] Error: {e}")`
- No structured exception classes defined — raw `Exception` used throughout
- FastAPI routes use `raise HTTPException(404, "Search not found")` for not-found cases
- No 400/422 error customization — FastAPI handles Pydantic validation errors automatically
- `try/except Exception as e` around `db.save_search()` with `console.print(f"[red]Could not save: {e}[/red]")`
- SMTP errors caught with `except Exception as e: print(f"[Report] Failed: {e}")`, returns `False`
- All async API calls wrapped in `try/catch`, errors sent to `console.error`:
- No user-facing error UI for API failures (errors logged only, no toast/alert shown)
- `api.js` throws `new Error(`API error: ${res.status}`)` on non-OK HTTP responses
## Logging
- Prefixed log lines with source in brackets: `print(f"[{provider.name}] Error: {e}")`, `print("[Report] Email sent to ...")`
- `rich.console.Console` used exclusively in CLI (`homesearch/main.py`) for styled output
- No structured logging (`logging` module not used anywhere)
- `console.error()` for caught exceptions only
- No `console.log()` in production paths
## Comments
- Module-level docstrings on every `.py` file describing purpose: `"""FastAPI REST API for the web frontend."""`
- Class docstrings on Pydantic models: `"""All possible search filters. Every field is optional."""`
- Function docstrings on public functions; private helpers (`_safe_float`, `_row_to_listing`) have no docstrings
- Inline comments used liberally for section headers: `# 1. Listing type`, `# Rate limiting - be respectful`
- JSX block comments (`{/* ... */}`) used as section dividers within JSX: `{/* Location + Radius */}`
- Inline `//` comments for logic clarification
## Function Design
- Python: Most functions under 40 lines. `search_interactive()` in `homesearch/main.py` is ~130 lines (intentionally long CLI wizard)
- JSX: Components under 200 lines; `SearchForm` is the longest at ~395 lines due to inline JSX
- Pydantic models used for multi-field inputs (`SearchCriteria`, `SearchRequest`)
- `**kwargs` used in `database.update_search()` for dynamic SQL updates
- Optional parameters use `Optional[T] = None` annotation (Python) or `= false` / `= null` defaults (JS)
- Python functions return typed values: `list[Listing]`, `list[SavedSearch]`, `Optional[SavedSearch]`, `bool`, `int`
- Functions that can find nothing return `[]` or `None` (never raise)
- Boolean success pattern used for side-effect operations: `send_email_report()` returns `True/False`
## Module Design
- No `__all__` defined in any module
- Public API implied by naming (`_` prefix = private)
- `homesearch/__init__.py` is empty (package marker only)
- `homesearch/providers/__init__.py` is empty (package marker only)
- `homesearch/services/__init__.py` is empty (package marker only)
- Single default export per component file: `export default function Dashboard()`
- Named export for API singleton: `export const api = { ... }` in `src/api.js`
- No barrel (`index.js`) files
## Pydantic Usage
- All models inherit from `pydantic.BaseModel`
- `Field(default_factory=list)` used for mutable list defaults
- `model_dump_json()` / `model_validate_json()` used for SQLite JSON serialization
- `model_copy(update={...})` used for immutable criteria updates in `search_service.py`
- `pydantic_settings.BaseSettings` used for config with `.env` loading in `homesearch/config.py`
## Provider Pattern
- Abstract base class `BaseProvider` in `homesearch/providers/base.py` defines the interface
- `search(criteria: SearchCriteria) -> list[Listing]` is the single required method
- `name` and `enabled` are abstract/overridable properties
- Concrete providers: `HomeHarvestProvider` (`homesearch/providers/homeharvest_provider.py`), `RedfinProvider` (`homesearch/providers/redfin_provider.py`)
- Private mapping constants (`_LISTING_TYPE_MAP`) defined at module level in provider files
- Module-level `_safe_float` and `_safe_int` helpers duplicated across both provider files (not shared)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Provider pattern: all real estate data sources implement `BaseProvider` and are registered in `search_service.py`
- Dual interface: the same Python package exposes both a Typer CLI and a FastAPI HTTP server
- Frontend is a pre-built static SPA served directly from FastAPI via `StaticFiles`; in dev, Vite proxies `/api` to the backend
- Persistence is SQLite via raw `sqlite3` (no ORM); the database module is a plain function library (`database.py`)
- Pydantic models are the shared data contract used by CLI, API, providers, and database layer
## Layers
- Purpose: Define shared data shapes used everywhere
- Location: `homesearch/models.py`
- Contains: `SearchCriteria`, `Listing`, `SavedSearch`, `ZipInfo`, `ListingType`, `PropertyType` enums
- Depends on: Pydantic only
- Used by: All other layers
- Purpose: Load typed settings from environment / `.env`
- Location: `homesearch/config.py`
- Contains: `Settings` (pydantic-settings `BaseSettings`), singleton `settings`
- Depends on: `pydantic-settings`
- Used by: `database.py`, `scheduler_service.py`, `report_service.py`, `main.py`
- Purpose: All SQLite read/write operations; no ORM
- Location: `homesearch/database.py`
- Contains: Schema DDL, connection factory, CRUD functions for saved searches, listings, search results linkage
- Depends on: `config.py`, `models.py`, `sqlite3`
- Used by: `search_service.py`, `report_service.py`, `api/routes.py`, `main.py`
- Purpose: Fetch raw listings from an external data source and normalize them to `Listing`
- Location: `homesearch/providers/`
- Contains: `BaseProvider` (ABC), `HomeHarvestProvider` (Realtor.com/MLS via `homeharvest`), `RedfinProvider` (Redfin via `redfin`)
- Depends on: `models.py`, third-party scraping libraries
- Used by: `search_service.py` only
- Purpose: Orchestrate business logic; does not own HTTP or CLI concerns
- Location: `homesearch/services/`
- Contains:
- Depends on: `models.py`, `database.py`, `providers/`, `config.py`
- Used by: `api/routes.py`, `main.py`
- Purpose: FastAPI REST endpoints consumed by the React frontend; also serves the built SPA
- Location: `homesearch/api/routes.py`
- Contains: FastAPI `app` instance, request/response models, all `/api/*` routes, static file mount
- Depends on: `services/`, `database.py`, `models.py`
- Used by: Frontend, and by `main.py` (`serve` command) via `uvicorn.run`
- Purpose: Typer CLI for interactive wizard, server launch, saved search management, report dispatch
- Location: `homesearch/main.py`
- Contains: `app` Typer instance, `search` / `serve` / `report` commands, `saved` sub-commands
- Depends on: `services/`, `database.py`, `models.py`, `config.py`
- Used by: Package entry point `homesearch = "homesearch.main:app"` in `pyproject.toml`
- Purpose: React SPA for web-based search, results browsing, and report triggering
- Location: `frontend/`
- Contains: Vite + React 18, TanStack Query for data fetching, React Router v6 pages, Tailwind CSS
- Depends on: Backend `/api/*` endpoints via `frontend/src/api.js`
- Used by: End users; served as static files from FastAPI in production
## Data Flow
- TanStack Query (`@tanstack/react-query`) manages all server state (fetching, caching, invalidation)
- No client-side global state store; component-local `useState` for form state
- `frontend/src/api.js` is the single fetch abstraction (plain `fetch`, no SDK)
## Key Abstractions
- Purpose: Plugin interface that all data source adapters must implement
- Examples: `homesearch/providers/base.py`, `homesearch/providers/homeharvest_provider.py`, `homesearch/providers/redfin_provider.py`
- Pattern: Abstract class with required `search(criteria) -> list[Listing]` and `name` property; optional `enabled` property for disabling without removal
- Purpose: Single Pydantic model carrying all search parameters between CLI, API, providers, and database
- Examples: `homesearch/models.py:SearchCriteria`
- Pattern: All fields optional; criteria is serialized as JSON into `saved_searches.criteria_json` column
- Purpose: Normalized property record — every provider maps its raw output to this shape
- Examples: `homesearch/models.py:Listing`
- Pattern: Source-agnostic; carries `source` and `source_id` fields for provenance tracking and deduplication
- Purpose: Persisted search profile — links a user-named search to its criteria and run history
- Examples: `homesearch/models.py:SavedSearch`
- Pattern: Stored with `criteria_json` (JSON-serialized `SearchCriteria`), `last_run_at` timestamp, `is_active` flag for report scheduling
## Entry Points
- Location: `homesearch/main.py` — `app` Typer instance
- Triggers: `homesearch` command via `pyproject.toml` script entry `homesearch.main:app`
- Responsibilities: Interactive search wizard, `serve` (launches uvicorn), `report`, `saved` subcommands
- Location: `homesearch/api/routes.py` — `app` FastAPI instance
- Triggers: `uvicorn.run("homesearch.api.routes:app", ...)` called from `main.py:serve()`
- Responsibilities: All `/api/*` REST endpoints, serving built frontend SPA from `frontend/dist/`
- Location: `frontend/src/main.jsx`
- Triggers: Browser load of `index.html`
- Responsibilities: Mount React app, wrap with `QueryClientProvider` and `BrowserRouter`
## Error Handling
- Provider `search()` methods wrap their entire body in `try/except`, log via `print`, return empty list on failure
- `_row_to_listing()` in providers catches per-row exceptions individually, returns `None` and skips bad rows
- FastAPI routes raise `HTTPException(404)` for missing resources; no global error handler is defined
- CLI commands use Rich console output with color-coded error messages; no exceptions bubble to user
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
