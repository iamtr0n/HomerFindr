# HomeSearch Aggregator

Universal real estate search tool that aggregates listings from **all major platforms** into one interface. Find your perfect home fast before it gets snatched up.

## Features

- **Multi-platform search** - Realtor.com (MLS), Redfin, with pluggable support for Zillow and others
- **Rich filtering** - Price, beds, baths, sq footage, lot size, year built, floors, basement, garage, HOA
- **Radius search** - Search by city/ZIP + mile radius (5-100 miles)
- **ZIP code discovery** - See all ZIP codes in your area, exclude neighborhoods you don't want
- **Dual interface** - Full CLI with interactive wizard + web dashboard with property cards
- **Saved searches** - Save and re-run searches, toggle active/inactive
- **Daily email reports** - Get new listings at 7 AM every morning
- **Property thumbnails** - See photos, click to open on the original listing site

## Quick Start

### 1. Install

```bash
# Clone the repo
git clone <repo-url>
cd HomeSearch

# Install Python package
pip install -e .
```

### 2. CLI Usage

```bash
# Interactive search wizard
homesearch search

# Launch web UI
homesearch serve

# List saved searches
homesearch saved list

# Run a saved search
homesearch saved run "My Dallas Search"

# Run all active searches
homesearch saved run --all

# Generate and send email report
homesearch report
```

### 3. Web UI

```bash
# Install frontend dependencies (one time)
cd frontend && npm install && npm run build && cd ..

# Start the server
homesearch serve

# Open http://127.0.0.1:8000
```

### 4. Email Reports (Optional)

Copy `.env.example` to `.env` and configure SMTP:

```bash
cp .env.example .env
# Edit .env with your email settings (Gmail app password recommended)
```

The server (`homesearch serve`) automatically schedules reports at 7:00 AM, or run `homesearch report` manually.

## CLI Search Wizard

The interactive wizard walks you through:

1. **Type** - Buy / Rent / Sold
2. **Property** - House, Condo, Townhouse, Multi-Family, Commercial, Land
3. **Location** - City, State or ZIP code
4. **Radius** - 5, 10, 25, 50 miles
5. **ZIP Discovery** - Shows all ZIP codes in area, lets you exclude any
6. **Price range**
7. **Beds / Baths**
8. **Square footage**
9. **Lot size**
10. **Year built**
11. **Floors / Stories**
12. **Basement** - Yes / No / Don't care
13. **Garage** - Yes / No / Don't care
14. **HOA max**
15. **Save search** - Name it for daily reports

All filters are optional - press Enter to skip any.

## Data Sources

| Source | Cost | How |
|--------|------|-----|
| Realtor.com (MLS) | Free | `homeharvest` package |
| Redfin | Free | `redfin` package |
| Zillow (future) | ~$10-30/mo | RapidAPI adapter |

## Adding New Providers

Create a new file in `homesearch/providers/`:

```python
from homesearch.providers.base import BaseProvider
from homesearch.models import Listing, SearchCriteria

class MyProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "mysite"

    def search(self, criteria: SearchCriteria) -> list[Listing]:
        # Fetch and return normalized listings
        ...
```

Then register it in `homesearch/services/search_service.py` in `get_providers()`.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLite
- **CLI**: Typer + Rich
- **Frontend**: React, Tailwind CSS, React Query
- **Data**: homeharvest, redfin (both free, no API keys)
- **Scheduler**: APScheduler
- **Email**: SMTP (Gmail, Outlook, etc.)
