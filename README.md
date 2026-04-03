<div align="center">

```
██╗  ██╗ ██████╗ ███╗   ███╗███████╗██████╗ 
██║  ██║██╔═══██╗████╗ ████║██╔════╝██╔══██╗
███████║██║   ██║██╔████╔██║█████╗  ██████╔╝
██╔══██║██║   ██║██║╚██╔╝██║██╔══╝  ██╔══██╗
██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗██║  ██║
╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
███████╗██╗███╗   ██╗██████╗ ██████╗ 
██╔════╝██║████╗  ██║██╔══██╗██╔══██╗
█████╗  ██║██╔██╗ ██║██║  ██║██████╔╝
██╔══╝  ██║██║╚██╗██║██║  ██║██╔══██╗
██║     ██║██║ ╚████║██████╔╝██║  ██║
╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝
```

### *"Can't believe I missed another listing! Doh!"*

**Search every home listing. Find the one.**

Pulls listings from Realtor.com, Redfin, and Zillow into one place — with a polished CLI and a full web dashboard. No browser juggling. No missed listings.

[![Version](https://img.shields.io/badge/version-1.2.0-amber)](https://github.com/iamtr0n/HomerFindr/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey)](https://github.com/iamtr0n/HomerFindr)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Install](#-install) · [Web Dashboard](#-web-dashboard) · [CLI](#-cli) · [Alerts](#-alerts--sms) · [Developers](#-for-developers)

</div>

---

## What is HomerFindr?

HomerFindr is a **local home search aggregator** that runs entirely on your machine. It queries Realtor.com (MLS), Redfin, and Zillow simultaneously and combines the results into one clean view — no duplicate listings, no paid APIs, no cloud dependency.

It has two interfaces that share the same data:

| Interface | Best for |
|-----------|----------|
| **Web Dashboard** | Browsing, filtering, saving, and tracking listings visually |
| **CLI (Terminal)** | Power users, quick searches, arrow-key navigation with zero typing |

Everything persists locally in SQLite. Saved searches run on a schedule and send desktop notifications or SMS alerts when new listings appear.

---

## ✨ Features at a Glance

- **3 data sources** — Realtor.com (MLS), Redfin, Zillow — deduplicated and merged
- **19+ search filters** — price, beds/baths, sqft, lot size, year built, HOA, garage, basement, pool, A/C, fireplace, heat type, house style, school rating, and more
- **Match scoring** — listings scored and ranked by how many of your criteria they hit; gold star ⭐ for perfect matches
- **Mortgage calculator** — live monthly payment estimate on every card, color-coded against your budget
- **Map view** — draw a polygon on a map to search a custom geographic area
- **Saved searches** — save any search, run it again anytime, get alerts on new listings
- **Price change tracking** — see when a listing's price drops or rises since you first saw it
- **SMS / webhook alerts** — new listings trigger Zapier webhooks (free SMS, email, Slack, etc.)
- **Desktop notifications** — cross-platform (macOS, Windows, Linux)
- **Highway proximity detection** — flag listings near major highways
- **No typing in CLI** — entire search wizard navigable with arrow keys and Enter
- **Backup to GitHub** — one command snapshots your database to a GitHub release

---

## 📦 Install

### macOS — One Command

Open **Terminal** and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/iamtr0n/HomerFindr/main/install.sh | bash
```

The installer will:
1. Check for Python 3.11+, Node.js, and Git — and offer to install any that are missing (via Homebrew)
2. Clone HomerFindr to `~/HomerFindr`
3. Build the React web dashboard
4. Register a background service that starts automatically at login
5. Open the dashboard in your browser

---

### macOS — Double-Click (for friends & family)

Download **[HomerFindr-Install.command](https://github.com/iamtr0n/HomerFindr/releases/latest/download/HomerFindr-Install.command)** and double-click it.

> **First time only:** If macOS says *"cannot be opened because the developer cannot be verified"*, right-click the file → **Open** → **Open**. macOS remembers your choice after that.

---

### Windows — One Command

Open **PowerShell** and paste:

```powershell
irm https://raw.githubusercontent.com/iamtr0n/HomerFindr/main/install.ps1 | iex
```

The installer will:
1. Check for Python 3.11+, Node.js, and Git — and install any that are missing via winget
2. Clone HomerFindr to `%LocalAppData%\HomerFindr`
3. Build the React web dashboard
4. Register a Task Scheduler entry so HomerFindr starts automatically at login
5. Create a desktop shortcut and open the dashboard

---

### Windows — Double-Click (for friends & family)

Download **[HomerFindr-Install.bat](https://github.com/iamtr0n/HomerFindr/releases/latest/download/HomerFindr-Install.bat)** and double-click it.

> No admin rights required — the installer handles PowerShell execution policy automatically for the install session only.

---

### After Install

Open your browser to **http://127.0.0.1:8000** — HomerFindr is running.

To use the CLI instead:
```bash
homerfindr        # interactive TUI (arrow keys)
homerfindr serve  # start the web server manually
```

---

## 🌐 Web Dashboard

The web dashboard is a React app served by the local FastAPI backend. Open it at `http://127.0.0.1:8000`.

---

### Dashboard

The home screen organizes listings into four sections — a listing only appears in one section at a time (highest priority first):

| Section | What's here |
|---------|-------------|
| **🆕 New Listings** | Listings found since the last time you ran a search |
| **⭐ Saved** | Listings you've starred — your shortlist |
| **🕐 Recent** | Listings from your most recent search run |
| **📋 All Listings** | Everything else in the database |

Each listing card shows:
- Address, price, beds/baths, sqft
- Source (Realtor.com / Redfin / Zillow) and days on market
- Match score badges (garage ✓, basement ✓, pool ✓, price ✓, etc.)
- Gold star ⭐ for perfect matches (hits every filter)
- Price change indicator (↓ drop / ↑ rise since first seen)
- Estimated monthly mortgage payment (when Mortgage Calculator is on)
- Dismiss button to hide a listing

---

### New Search

A full-featured search form with every filter exposed:

**Location & Scope**
- City/state or ZIP code + radius in miles
- ZIP code discovery (auto-finds all ZIPs within radius)
- Multi-area mode (combine searches across multiple cities)
- Exclude specific ZIP codes from results

**Listing Type & Property**
- Listing type: For Sale, For Rent, Sold, Pending, Coming Soon
- Property type: Single Family, Condo, Townhouse, Multi-Family, Commercial, Land
- House style: Ranch, Colonial, Victorian, Contemporary, Craftsman, Cape Cod, and more

**Price & Size**
- Min/max price
- Min/max square footage
- Min/max lot size
- Affordability filter: enter a monthly budget and HomerFindr auto-calculates the max price based on your mortgage settings

**Bedrooms & Bathrooms**
- Minimum bedrooms
- Minimum bathrooms

**Features**
- Garage (yes / no / either) + minimum garage spaces
- Basement (yes / no / either)
- Pool (yes / no / either)
- Fireplace (required / excluded)
- Central A/C (yes / no / either)
- Heat type: Gas, Electric, Oil, Solar, any

**Other Filters**
- Year built min/max
- Max HOA monthly fee (0 = no HOA)
- Minimum school rating
- Minimum stories
- Avoid highway proximity
- Days pending minimum (filter pending listings by how long they've been pending)
- Style strict mode (hide listings where house style couldn't be detected)

Search results stream in live with a progress terminal showing which ZIP codes are being queried.

---

### Search Results

After a search runs, results are ranked by match score with the best listings first. You can filter further with inline controls:

- **Price range slider** — narrow results without re-running the search
- **Min beds / min baths** — quick filter
- **Hide viewed** — collapses listings you've already opened
- **Sort** — by match score, price (low/high), or newest

Each result shows the full listing card with all badges, plus a direct link to the original listing on Realtor.com, Redfin, or Zillow.

---

### Map View

Draw a polygon on an interactive map to define a custom search area. HomerFindr finds all ZIP codes within the polygon and runs a search. Useful for targeting a specific neighborhood, school district, or commute zone without knowing ZIP codes.

---

### Mortgage Calculator

A toolbar that sits above the results. Toggle it on to see estimated monthly payments on every listing card.

| Setting | What it does |
|---------|-------------|
| **Rate** | Annual interest rate (%) |
| **Down** | Down payment percentage |
| **Term** | Loan term: 10, 15, 20, or 30 years |
| **Budget** | Your target monthly payment |

When a budget is set, payment amounts are **color-coded**:
- 🟢 Green — at or under budget
- 🟡 Yellow — within 20% over budget  
- 🔴 Red — more than 20% over budget

Settings persist across sessions in `localStorage`.

---

### Settings

Configure notifications and integrations:

**Email Reports**
- Enter your SMTP credentials to receive daily email summaries of new listings across all saved searches
- Test SMTP connection from the UI
- Configure report time (default: 7:00 AM)

**Zapier Webhook (SMS / Slack / etc.)**
- Enter a Zapier Catch Hook URL to receive real-time alerts when new listings are found
- Per-search webhook URLs supported (override the global URL for specific searches)
- Test webhook from the UI

**Scheduler**
- Configure how often saved searches run automatically (default: every 60 minutes)
- Toggle active/inactive per saved search

---

## 💻 CLI

The CLI runs entirely in the terminal with no mouse needed. Every step is navigable with arrow keys and Enter.

```bash
homerfindr           # Launch the interactive TUI (default)
homerfindr search    # Run the search wizard directly
homerfindr serve     # Start the web server
homerfindr saved     # Manage saved searches
homerfindr report    # Send email report now
```

### Interactive TUI

The default `homerfindr` command launches the full-screen terminal UI:

```
┌─────────────────────────────────────┐
│  🏠 HomerFindr                      │
│  ─────────────────────────────────  │
│  ▶  New Search                      │
│     Saved Searches                  │
│     Run All Saved Searches          │
│     Open Web Dashboard              │
│     Settings                        │
│     Quit                            │
└─────────────────────────────────────┘
```

### Search Wizard

`homerfindr search` walks you through a 19-step wizard — no typing required on any step:

1. Listing type (For Sale / Rent / Sold / Pending / Coming Soon)
2. Property type (House / Condo / Townhouse / Multi-family / etc.)
3. Location (city, state or ZIP)
4. Search radius
5. ZIP code discovery and exclusion
6. Price range
7. Bedrooms minimum
8. Bathrooms minimum
9. Sqft range
10. Lot size range
11. Year built range
12. Garage (yes / no / either)
13. Basement (yes / no / either)
14. Pool (yes / no / either)
15. Fireplace / A/C / heat type
16. HOA max
17. House style
18. School rating minimum
19. Highway avoidance

After the wizard, a spinner shows live search progress across all ZIP codes. Results display in a color-coded table, ranked by match score.

### Saved Search Commands

```bash
homerfindr saved list          # list all saved searches
homerfindr saved run <name>    # run a saved search
homerfindr saved delete <name> # delete a saved search
homerfindr saved toggle <name> # enable/disable alerts
```

---

## 🔔 Alerts & SMS

HomerFindr checks your saved searches on a schedule and alerts you when new listings appear.

### Desktop Notifications

Enabled per saved search in Settings. Works on macOS, Windows, and Linux (requires `plyer`). Shows a native system notification with the address and search name.

### SMS / Webhook Alerts (Free via Zapier)

1. Create a free account at [zapier.com](https://zapier.com)
2. Create a new Zap: **Webhooks by Zapier** → **SMS by Zapier** (or Slack, Gmail, etc.)
3. Copy the Catch Hook URL
4. Paste it into HomerFindr Settings → Zapier Webhook

When a new listing is found, HomerFindr sends a JSON payload to your Zapier hook:

```json
{
  "search_name": "Austin under 500k",
  "new_count": 3,
  "listings": [
    {
      "address": "123 Oak Lane, Austin TX",
      "price": 449000,
      "beds": 3,
      "baths": 2,
      "sqft": 1850,
      "url": "https://www.realtor.com/..."
    }
  ]
}
```

---

## 💾 Backup

HomerFindr stores all your data locally in `~/.homesearch/homesearch.db`. Back it up with one command:

```bash
make backup          # create local snapshot → ~/.homesearch/backups/
make backup-push     # create snapshot + upload to GitHub releases
make restore-github  # download latest GitHub backup and restore
```

Backups include:
- `homesearch.db` — all saved searches, listings, price history, notes
- `.env` — your Zapier/SMTP configuration
- `vapid_private.pem` — push notification keys

GitHub backups are stored at: **[releases/tag/backups](https://github.com/iamtr0n/HomerFindr/releases/tag/backups)**

To schedule daily automatic backups at 3 AM:
```bash
make setup-backup
```

---

## 🔄 Update

Re-run your original installer — it detects an existing install, pulls the latest code, and rebuilds:

**macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/iamtr0n/HomerFindr/main/install.sh | bash
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/iamtr0n/HomerFindr/main/install.ps1 | iex
```

Or if you cloned the repo:
```bash
make update
```

---

## 🛠 For Developers

### Requirements

- Python 3.11+
- Node.js (any modern LTS)
- Git

### Quick Start

```bash
git clone https://github.com/iamtr0n/HomerFindr.git
cd HomerFindr
make install    # installs Python package via pipx + builds frontend
homerfindr serve
```

### Makefile Commands

```bash
make build          # rebuild the React frontend
make deploy         # build + sync to running Homebrew install + restart service
make update         # git pull + rebuild + redeploy
make backup         # back up DB + config → ~/.homesearch/backups/
make backup-push    # backup + upload to GitHub releases
make restore-github # download latest GitHub backup and restore
make restore F=<f>  # restore from a specific backup file
make setup-backup   # schedule daily auto-backup at 3 AM (macOS launchd)
make list-backups   # show all local backups
make launchers      # ensure launcher files are executable
make release V=x.y.z# bump version, tag, push → GitHub Actions builds installers
make clean          # remove build artifacts
```

### Release Process

```bash
make release V=1.3.0
```

This will:
1. Bump the version in `pyproject.toml`
2. Create a git tag `v1.3.0`
3. Push to GitHub
4. GitHub Actions builds the release:
   - Computes sha256 of the release tarball
   - Updates `homebrew-formula/homerfindr.rb`
   - Creates a GitHub Release with `install.sh`, `install.ps1`, `HomerFindr-Install.command`, and `HomerFindr-Install.bat` attached
5. Snapshot your current database to the GitHub backups release

### Project Structure

```
HomerFindr/
├── homesearch/               # Python package
│   ├── api/routes.py         # FastAPI REST API
│   ├── providers/            # Data sources (Realtor.com, Redfin, Zillow)
│   ├── services/             # Search, scheduler, zip discovery, reports
│   ├── tui/                  # Terminal UI (wizard, results, splash)
│   ├── database.py           # SQLite layer
│   ├── models.py             # Pydantic models
│   └── main.py               # CLI entry point (Typer)
├── frontend/                 # React + Vite web dashboard
│   └── src/
│       ├── pages/            # Dashboard, NewSearch, SearchResults, MapView, Settings
│       └── components/       # PropertyCard, MortgageBar, SearchForm, ListingMap, ...
├── packaging/                # Distributable launchers
│   ├── HomerFindr-Install.command   # macOS double-click installer
│   └── HomerFindr-Install.bat       # Windows double-click installer
├── scripts/                  # Backup scripts
├── homebrew-formula/         # Homebrew formula (auto-updated by CI)
├── install.sh                # macOS curl installer
├── install.ps1               # Windows PowerShell installer
└── Makefile                  # Build, deploy, backup, release automation
```

### Environment Variables (`.env`)

```bash
# Server
HOST=127.0.0.1
PORT=8000

# Database
DATABASE_PATH=~/.homesearch/homesearch.db

# Email reports
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your_app_password
REPORT_EMAIL=you@gmail.com
REPORT_HOUR=7
REPORT_MINUTE=0

# Alerts
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/hooks/catch/...
```

---

## 📋 Changelog

### v1.2.0 — 2026-03-26

**New**
- Mortgage calculator bar with live monthly payment on every card, color-coded against budget
- Affordability filter: enter a monthly budget, price max auto-calculates
- Map view: draw a polygon to define a custom search area
- Dashboard section deduplication: each listing appears in exactly one section (New → Saved → Recent → All)
- Price change tracking with ↑/↓ indicators on listing cards
- Zillow provider added as third data source
- Cross-platform desktop notifications via `plyer` (replaces macOS-only osascript)
- Version badge in nav bar (live from API)
- Windows installer (`install.ps1`) with winget auto-install and Task Scheduler
- Double-click launchers: `HomerFindr-Install.command` (Mac) and `HomerFindr-Install.bat` (Windows)
- GitHub backup release: `make backup-push` uploads DB snapshots to GitHub
- `Makefile` with full build, deploy, backup, and release automation
- `GET /api/version` endpoint

**Bug Fixes**
- `_passes_filters`: all numeric filters now correctly handle `None` values (was causing zero results when filters were set)
- `listing_types` filter changed from blocklist to allowlist
- Dashboard: fixed wrong props on New Listings cards
- SearchResults: `filteredAndSorted` converted to `useMemo`; fixed stale closure
- ListingMap: fixed `pm:create` listener leak removing all listeners on cleanup
- MapView: fixed polygon zip_codes response key
- Scheduler: `startup_catchup` now uses `DateTrigger` (one-shot); webhook job corrected to 3-minute interval
- `get_starred_listings`: fixed `SELECT DISTINCT` to `GROUP BY` to correctly surface `is_new` flag
- `upsert_listing`: structural fields (beds, baths, sqft, etc.) now update via `COALESCE`

---

### v1.1.0 — 2026-03-20

- Live "found so far" counter during ZIP search spinner
- Multi-provider deduplication by normalized address
- Match scoring with badges (garage, basement, pool, HOA, beds/baths, price, new build)
- Gold star ⭐ for perfect matches
- Highway proximity enrichment
- Saved search browser with run/rename/delete/toggle
- House style filter with descriptions
- School rating filter, HOA max filter

---

### v1.0.0 — 2026-03-01

- Initial release
- Realtor.com + Redfin providers
- Interactive TUI wizard with ZIP code discovery
- FastAPI + React web dashboard
- SQLite persistence
- Daily email reports via APScheduler

---

<div align="center">

Made with ☕ for house hunters who hate missing listings.

**[⭐ Star this repo](https://github.com/iamtr0n/HomerFindr)** if HomerFindr helped you find a home.

</div>
