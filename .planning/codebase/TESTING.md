# Testing Patterns

**Analysis Date:** 2026-03-25

## Test Framework

**Runner:**
- Python: `pytest` (declared as optional dev dependency in `pyproject.toml`)
  - `pytest>=8.0`
  - `pytest-asyncio>=0.23`
- JavaScript: No test framework installed. No `vitest`, `jest`, or any testing library in `frontend/package.json`
- Config: No `pytest.ini`, `setup.cfg`, `conftest.py`, `jest.config.*`, or `vitest.config.*` present

**Assertion Library:**
- Python: pytest built-in assertions (implied by `pytest` dependency)
- JavaScript: Not applicable — no test framework configured

**Run Commands:**
```bash
# Python (from project root)
pip install -e ".[dev]"     # Install dev dependencies including pytest
pytest                       # Run all tests (no tests currently exist)

# JavaScript
# No test runner configured
```

## Current Test State

**No tests exist in this codebase.**

A search across all directories finds zero `*.test.*`, `*.spec.*`, `test_*.py`, or `*_test.py` files. The only testing infrastructure present is the dev dependency declaration in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]
```

No `conftest.py`, no test directories, no test files of any kind.

## Recommended Test Structure (for new tests)

Based on the project layout and Python conventions, tests should follow this structure when added:

**Location:**
- Python tests: `tests/` directory at project root (create it)
- Test files: `tests/test_<module>.py` naming pattern

**Recommended directory layout:**
```
tests/
├── conftest.py                  # Shared fixtures
├── test_models.py               # Pydantic model validation tests
├── test_search_service.py       # run_search, _passes_filters, _normalize_address
├── test_zip_service.py          # discover_zip_codes, _parse_city, _parse_state
├── test_database.py             # SQLite CRUD operations
├── test_providers/
│   ├── test_homeharvest_provider.py
│   └── test_redfin_provider.py
└── test_api/
    └── test_routes.py           # FastAPI endpoint tests
```

## Key Functions Worth Testing

**Pure logic (no I/O, easiest to test):**

`homesearch/services/search_service.py`:
- `_normalize_address(address)` — normalizes street abbreviations
- `_listing_quality(listing)` — returns integer score for listing completeness
- `_passes_filters(listing, criteria)` — boolean filter logic (many branches to cover)

`homesearch/services/zip_service.py`:
- `_parse_city(location)` — splits "City, State" strings
- `_parse_state(location)` — extracts state from location string

`homesearch/providers/homeharvest_provider.py`:
- `_safe_float(val)` — handles None, NaN, bad types
- `_safe_int(val)` — delegates to `_safe_float`

`homesearch/providers/redfin_provider.py`:
- `_safe_float(val)` — duplicate of above (same signature)
- `_map_property_type(ptype)` — string → property type enum value

**Note:** `_safe_float` and `_safe_int` are duplicated verbatim between `homeharvest_provider.py` and `redfin_provider.py`. Tests should cover both instances until the duplication is resolved.

## Patterns for When Tests Are Written

**Pytest fixture pattern (recommended for this codebase):**
```python
# tests/conftest.py
import pytest
from homesearch.models import SearchCriteria, Listing, ListingType

@pytest.fixture
def default_criteria():
    return SearchCriteria(location="Chicago, IL", radius_miles=25)

@pytest.fixture
def sample_listing():
    return Listing(
        source="realtor",
        source_id="test-123",
        address="123 Main St, Chicago, IL",
        city="Chicago",
        state="IL",
        zip_code="60601",
        price=350000,
        bedrooms=3,
        bathrooms=2.0,
        sqft=1800,
    )
```

**Unit test pattern for pure functions:**
```python
# tests/test_search_service.py
from homesearch.services.search_service import _normalize_address, _passes_filters
from homesearch.models import SearchCriteria, Listing

def test_normalize_address_abbreviates_street():
    assert _normalize_address("123 Main Street") == "123 main st"

def test_normalize_address_handles_commas():
    assert _normalize_address("123 Main St, Chicago") == "123 main st chicago"

def test_passes_filters_price_min(sample_listing, default_criteria):
    default_criteria.price_min = 400000
    assert _passes_filters(sample_listing, default_criteria) is False
```

**Async test pattern (for any future async code):**
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

**FastAPI endpoint test pattern:**
```python
# tests/test_api/test_routes.py
import pytest
from fastapi.testclient import TestClient
from homesearch.api.routes import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    return TestClient(app)

def test_list_searches_empty(client):
    response = client.get("/api/searches")
    assert response.status_code == 200
    assert response.json()["searches"] == []
```

## Mocking

**Framework:** `unittest.mock` (stdlib) or `pytest-mock` (not yet installed)

**What to mock when adding tests:**
- `homeharvest.scrape_property()` — external scraper; mock the DataFrame return
- `redfin.Redfin().search()` — external HTTP; mock the response dict
- `uszipcode.SearchEngine` — offline DB; mock `by_zipcode`, `by_coordinates`
- `smtplib.SMTP` — mock for email tests in `homesearch/services/report_service.py`
- `homesearch.database` functions — mock for service layer unit tests

**What NOT to mock:**
- Pydantic model construction (test it directly)
- Pure helper functions (`_normalize_address`, `_passes_filters`, `_safe_float`)
- SQLite via `get_connection()` — use `tmp_path` fixture with `monkeypatch` on `settings.database_path` instead

**Provider mock pattern:**
```python
from unittest.mock import patch, MagicMock
import pandas as pd

def test_homeharvest_provider_search():
    mock_df = pd.DataFrame([{
        "street": "123 Main St", "city": "Chicago", "state": "IL",
        "zip_code": "60601", "list_price": 350000, "beds": 3, "baths": 2.0,
    }])
    with patch("homeharvest.scrape_property", return_value=mock_df):
        from homesearch.providers.homeharvest_provider import HomeHarvestProvider
        from homesearch.models import SearchCriteria
        provider = HomeHarvestProvider()
        results = provider.search(SearchCriteria(location="Chicago, IL", zip_codes=["60601"]))
        assert len(results) == 1
        assert results[0].price == 350000
```

## Coverage

**Requirements:** None enforced (no coverage config or CI pipeline)

**Recommended coverage targets when tests are added:**
- `homesearch/services/search_service.py` — HIGH priority (`_passes_filters` has ~20 branches)
- `homesearch/database.py` — HIGH priority (all CRUD paths)
- `homesearch/providers/` — MEDIUM priority (requires mocking external calls)
- `homesearch/services/report_service.py` — MEDIUM priority (SMTP path)
- `homesearch/api/routes.py` — MEDIUM priority (HTTP status codes)

**View coverage (once tests exist):**
```bash
pip install pytest-cov
pytest --cov=homesearch --cov-report=html
open htmlcov/index.html
```

## Test Types

**Unit Tests:**
- Intended scope: pure functions in `search_service.py`, `zip_service.py`, both provider helpers
- No external dependencies, no I/O

**Integration Tests:**
- Database: Use SQLite with temp file via `tmp_path` pytest fixture
- API: Use `fastapi.testclient.TestClient` (synchronous, no server needed)
- Providers: Requires mocking the third-party library calls

**E2E Tests:**
- Not configured. No Playwright, Cypress, or Selenium dependencies present.

## Notable Testing Gaps

The following areas have no test coverage and represent the highest risk:

1. `_passes_filters()` in `homesearch/services/search_service.py` — 25+ conditional branches; logic bugs would silently return wrong results
2. `upsert_listing()` in `homesearch/database.py` — update vs insert branching, boolean-to-int conversion for SQLite
3. `_row_to_listing()` in `homesearch/providers/homeharvest_provider.py` — DataFrame column name fallback chains
4. `discover_zip_codes()` in `homesearch/services/zip_service.py` — ZIP vs city/state parsing branch
5. All FastAPI routes — no HTTP status code or response shape validation

---

*Testing analysis: 2026-03-25*
