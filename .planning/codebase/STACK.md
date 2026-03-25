# Technology Stack

**Analysis Date:** 2026-03-25

## Languages

**Primary:**
- Python 3.11+ - Backend, CLI, API server, data providers, scheduling
- JavaScript (ES Modules) - Frontend React application

**Secondary:**
- JSX - React component templates (`frontend/src/**/*.jsx`)
- HTML - Single-page app shell (`frontend/index.html`)

## Runtime

**Environment:**
- Python 3.11+ (required by `pyproject.toml`: `requires-python = ">=3.11"`)
- Node.js (version not pinned; used only for frontend build tooling)

**Package Manager:**
- Python: `pip` with `setuptools>=68.0` build backend (`pyproject.toml`)
- Node: `npm` (`frontend/package.json`)
- Lockfiles: No `requirements.txt` lockfile; no `package-lock.json` detected (not committed)

## Frameworks

**Core Backend:**
- FastAPI `>=0.115.0` - REST API server (`homesearch/api/routes.py`)
- Uvicorn `>=0.30.0` (standard extras) - ASGI server, launched via `uvicorn.run()` in `homesearch/main.py`

**Core Frontend:**
- React `^18.3.1` - UI component framework (`frontend/src/`)
- React Router DOM `^6.26.0` - Client-side routing
- TanStack React Query `^5.51.0` - Server state and async data fetching
- Vite `^5.4.0` - Dev server and build tool (`frontend/vite.config.js`)

**CLI:**
- Typer `>=0.12.0` - CLI framework (`homesearch/main.py`)
- Rich `>=13.7.0` - Terminal output formatting, tables, prompts

**Testing:**
- pytest `>=8.0` (dev dependency)
- pytest-asyncio `>=0.23` (dev dependency)

**Build/Dev:**
- `@vitejs/plugin-react` `^4.3.1` - Vite plugin for React/JSX transform
- PostCSS `^8.4.40` - CSS processing pipeline
- Autoprefixer `^10.4.19` - CSS vendor prefixes

## Key Dependencies

**Data Scraping:**
- `homeharvest>=0.4.0` - Scrapes Realtor.com (MLS) listings; no API key required (`homesearch/providers/homeharvest_provider.py`)
- `redfin>=0.2.0` - Accesses Redfin stingray API; no API key required (`homesearch/providers/redfin_provider.py`)

**Data Validation:**
- `pydantic>=2.7.0` - Data models and validation (`homesearch/models.py`)
- `pydantic-settings>=2.3.0` - Settings management from env/`.env` file (`homesearch/config.py`)

**Data Processing:**
- `pandas>=2.2.0` - Used to process homeharvest DataFrame results

**Scheduling:**
- `apscheduler>=3.10.0` - Background cron scheduler for daily email reports (`homesearch/services/scheduler_service.py`)

**Geo/ZIP:**
- `uszipcode>=1.0.1` - Offline ZIP code database for radius discovery (`homesearch/services/zip_service.py`)
- `geopy>=2.4.0` - Geospatial utilities (imported as dependency, available for distance calculations)

**HTTP:**
- `httpx>=0.27.0` - Async HTTP client (available; used internally by dependencies)

**Async File I/O:**
- `aiofiles>=24.1.0` - Async file operations

**Templating:**
- `jinja2>=3.1.0` - HTML templating (available; email report uses inline string building currently)

**Multipart:**
- `python-multipart>=0.0.9` - Required by FastAPI for form data

**Frontend Icons:**
- `lucide-react` `^0.424.0` - Icon library for React UI

**Frontend CSS:**
- Tailwind CSS `^3.4.7` - Utility-first CSS framework (`frontend/tailwind.config.js`)

## Configuration

**Environment:**
- Settings loaded from `.env` file via `pydantic-settings` (`homesearch/config.py`)
- `.env.example` present at project root
- Key env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `REPORT_EMAIL`, `RAPIDAPI_KEY`, `HOST`, `PORT`, `REPORT_HOUR`, `REPORT_MINUTE`, `DATABASE_PATH`
- Defaults: SQLite at `~/.homesearch/homesearch.db`, server on `127.0.0.1:8000`, report at 07:00

**Build:**
- `frontend/vite.config.js` - Vite build config; dev server proxies `/api` to `http://127.0.0.1:8000`
- `frontend/tailwind.config.js` - Tailwind scans `./index.html` and `./src/**/*.{js,jsx}`
- `frontend/postcss.config.js` - PostCSS config (Tailwind + Autoprefixer)
- `pyproject.toml` - Python package metadata and dependencies

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js (any modern LTS; used for `npm install && npm run build`)
- Install Python package: `pip install -e .`
- Install frontend: `cd frontend && npm install`

**Production:**
- Self-hosted: runs as a single process (`homesearch serve`) on the local machine
- No containerization or cloud deployment config detected
- Frontend must be pre-built (`npm run build`) before serving; FastAPI serves the `frontend/dist/` directory as static files

---

*Stack analysis: 2026-03-25*
