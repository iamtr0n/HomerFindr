# External Integrations

**Analysis Date:** 2026-03-25

## APIs & External Services

**Real Estate Data (Free, No API Key):**
- Realtor.com / MLS - Source of for-sale, for-rent, and sold listings via web scraping
  - SDK/Client: `homeharvest` package (`homesearch/providers/homeharvest_provider.py`)
  - Auth: None required
  - Rate limiting: 1.5 second sleep between requests (built-in)
  - Data returned as pandas DataFrame; converted to `Listing` model

- Redfin - Source of for-sale, for-rent, and sold listings via internal stingray API
  - SDK/Client: `redfin` package (`homesearch/providers/redfin_provider.py`)
  - Auth: None required
  - Rate limiting: 2 second sleep between requests (built-in)
  - Data returned as nested JSON dicts; converted to `Listing` model

**Real Estate Data (Optional, Paid):**
- RapidAPI (Zillow adapter, future) - Planned provider for Zillow data
  - SDK/Client: Not yet implemented; adapter described in `README.md`
  - Auth: `RAPIDAPI_KEY` env var (`homesearch/config.py`)
  - Cost: ~$10–30/mo per README
  - Status: No provider file exists yet; env var is present but unused

## Data Storage

**Databases:**
- SQLite - Primary persistence layer for saved searches and cached listings
  - File location: `~/.homesearch/homesearch.db` (default) or overridden via `DATABASE_PATH` env var
  - Client: Python stdlib `sqlite3` module (`homesearch/database.py`)
  - ORM: None - raw SQL with parameterized queries
  - Schema: Three tables - `saved_searches`, `listings`, `search_results` (join table)
  - Initialized on startup via `db.init_db()` called from `homesearch/api/routes.py` and `homesearch/main.py`

**File Storage:**
- Local filesystem only - no cloud object storage
- Frontend static assets served from `frontend/dist/` by FastAPI (`homesearch/api/routes.py`)

**Caching:**
- No dedicated cache layer; listing results are persisted to SQLite and re-fetched on each search run

## Authentication & Identity

**Auth Provider:**
- None - no user authentication or authorization
- Application runs as a single-user local tool; all API endpoints are open (`CORSMiddleware` allows all origins in `homesearch/api/routes.py`)

## Email / Notifications

**SMTP Email:**
- Provider: Any SMTP server (Gmail default: `smtp.gmail.com:587`)
  - Implementation: Python stdlib `smtplib` with STARTTLS (`homesearch/services/report_service.py`)
  - Auth: `SMTP_USER`, `SMTP_PASSWORD` env vars
  - Recipient: `REPORT_EMAIL` env var
  - Content: HTML email with property thumbnails and listing details
  - Trigger: Daily cron at `REPORT_HOUR:REPORT_MINUTE` (default 07:00) or manual `homesearch report` command

## Scheduling

**APScheduler Background Scheduler:**
- Type: `BackgroundScheduler` with `CronTrigger` (`homesearch/services/scheduler_service.py`)
- Lifecycle: Started when `homesearch serve` launches, stopped on shutdown
- Job: `daily_report_job` - runs all active saved searches and emails results
- Schedule: Configurable via `REPORT_HOUR` / `REPORT_MINUTE` env vars

## Monitoring & Observability

**Error Tracking:**
- None - no external error tracking service (Sentry, Datadog, etc.)

**Logs:**
- `print()` statements to stdout throughout provider and service code
- No structured logging framework; no log rotation or aggregation

## CI/CD & Deployment

**Hosting:**
- Local machine only - no cloud hosting, no Dockerfile, no deployment manifests detected

**CI Pipeline:**
- None detected - no `.github/workflows/`, no CI config files

## Geographic Data

**uszipcode Offline Database:**
- ZIP code lookup and radius search with no outbound API calls
  - Client: `uszipcode.SearchEngine` (`homesearch/services/zip_service.py`)
  - Data: Bundled SQLite database shipped with the `uszipcode` package
  - Capabilities: Lookup by ZIP, city+state, or lat/lng radius (up to 200 results)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Environment Configuration

**Required env vars (for full functionality):**
- `SMTP_USER` - SMTP login username (email address)
- `SMTP_PASSWORD` - SMTP password or app-specific password
- `REPORT_EMAIL` - Recipient address for daily email reports

**Optional env vars (with defaults):**
- `DATABASE_PATH` - SQLite file path (default: `~/.homesearch/homesearch.db`)
- `SMTP_HOST` - SMTP server hostname (default: `smtp.gmail.com`)
- `SMTP_PORT` - SMTP port (default: `587`)
- `HOST` - Web server bind address (default: `127.0.0.1`)
- `PORT` - Web server port (default: `8000`)
- `REPORT_HOUR` - Daily report hour 0-23 (default: `7`)
- `REPORT_MINUTE` - Daily report minute 0-59 (default: `0`)
- `RAPIDAPI_KEY` - Future Zillow/RapidAPI key (currently unused)

**Secrets location:**
- `.env` file at project root (loaded by `pydantic-settings`; `.env.example` committed as template)

---

*Integration audit: 2026-03-25*
