# Coding Conventions

**Analysis Date:** 2026-03-25

## Naming Patterns

**Python Files:**
- `snake_case` for all module names: `search_service.py`, `zip_service.py`, `report_service.py`
- `snake_case` for package directories: `homesearch/`, `homesearch/providers/`, `homesearch/services/`
- Private helpers prefixed with `_`: `_safe_float`, `_safe_int`, `_row_to_listing`, `_normalize_address`, `_passes_filters`

**Python Classes:**
- `PascalCase` for all classes: `BaseProvider`, `HomeHarvestProvider`, `RedfinProvider`, `SearchCriteria`, `SavedSearch`
- `PascalCase` for Pydantic models: `Settings`, `ZipInfo`, `Listing`

**Python Functions:**
- `snake_case` for all functions and methods: `run_search`, `discover_zip_codes`, `get_saved_searches`
- CLI command functions use short imperative names: `search`, `serve`, `report`, `saved_list`, `saved_run`
- Helper functions in modules prefixed with `_`: `_parse_city`, `_parse_state`, `_listing_html`

**Python Variables:**
- `snake_case` throughout: `all_listings`, `zip_codes`, `listing_type`, `property_types`
- Module-level constants in `UPPER_SNAKE_CASE`: `SCHEMA`, `_LISTING_TYPE_MAP`
- Short loop variables acceptable for iterations: `l` for listing, `s` for search, `z` for zip

**JavaScript/JSX Files:**
- `PascalCase` for component files and component functions: `SearchForm.jsx`, `PropertyCard.jsx`, `Dashboard.jsx`
- `camelCase` for utilities: `api.js`
- Page components in `src/pages/`, reusable components in `src/components/`

**JavaScript Variables and Functions:**
- `camelCase` for variables and functions: `zipResults`, `zipLoading`, `discoverZips`, `toggleZipExclude`
- `UPPER_SNAKE_CASE` for module-level constant arrays: `LISTING_TYPES`, `PROPERTY_TYPES`, `TRISTATE`
- `camelCase` for event handlers: `handleSearch`, `set`, `setNum`

## Code Style

**Formatting:**
- No formatter config file detected (no `.prettierrc`, `biome.json`, or `.eslintrc`)
- Python: PEP 8 style, 4-space indentation
- JavaScript/JSX: 2-space indentation, single quotes for imports, template literals for string interpolation
- Trailing commas used in multi-line Python and JS structures

**Linting:**
- No ESLint or Prettier config detected in the project
- No `ruff`, `black`, or `flake8` config in `pyproject.toml`
- Code relies on developer discipline — no enforced tooling

## Import Organization

**Python Order (observed pattern):**
1. Standard library imports (`json`, `sqlite3`, `datetime`, `pathlib`, `typing`, `abc`, `smtplib`, `math`)
2. Third-party imports (`fastapi`, `pydantic`, `typer`, `rich`, `uvicorn`)
3. Local package imports (`from homesearch import ...`, `from homesearch.models import ...`)

**Python Import Style:**
- Module-level imports preferred; lazy imports inside functions used for optional dependencies:
  ```python
  def search(self, criteria):
      try:
          import homeharvest
      except ImportError:
          print("[HomeHarvest] Package not installed.")
          return []
  ```
- `from homesearch import database as db` aliased consistently across all modules
- Type imports via `from typing import Optional` (not `typing.Optional`)
- `from __future__ import annotations` used in `homesearch/models.py` for forward references

**JavaScript/JSX Order (observed pattern):**
1. React and router imports: `import { useState } from 'react'`
2. TanStack Query hooks: `import { useQuery, useMutation } from '@tanstack/react-query'`
3. Local API: `import { api } from '../api'`
4. Icon imports: `import { Search, Loader2 } from 'lucide-react'`
5. Local component imports

**Path Aliases:**
- None configured. All imports use relative paths: `'../api'`, `'../pages/Dashboard'`

## Error Handling

**Python — Provider Layer:**
- Providers wrap entire search logic in `try/except Exception` and call `traceback.print_exc()` then `continue`:
  ```python
  except Exception:
      traceback.print_exc()
      continue
  ```
- Per-location errors inside loops use `continue` to skip failing ZIPs, not abort entire search
- Optional dependency missing: caught with `ImportError`, prints install hint, returns empty list

**Python — Service Layer:**
- `run_search` in `homesearch/services/search_service.py` catches per-provider errors and logs with `print(f"[{provider.name}] Error: {e}")`
- No structured exception classes defined — raw `Exception` used throughout

**Python — API Layer:**
- FastAPI routes use `raise HTTPException(404, "Search not found")` for not-found cases
- No 400/422 error customization — FastAPI handles Pydantic validation errors automatically

**Python — CLI Layer:**
- `try/except Exception as e` around `db.save_search()` with `console.print(f"[red]Could not save: {e}[/red]")`
- SMTP errors caught with `except Exception as e: print(f"[Report] Failed: {e}")`, returns `False`

**JavaScript:**
- All async API calls wrapped in `try/catch`, errors sent to `console.error`:
  ```javascript
  try {
    const data = await api.discoverZips(...)
  } catch (e) {
    console.error('ZIP discovery failed:', e)
  }
  ```
- No user-facing error UI for API failures (errors logged only, no toast/alert shown)
- `api.js` throws `new Error(`API error: ${res.status}`)` on non-OK HTTP responses

## Logging

**Framework:** `print()` for Python backend, `console.error()` for JavaScript

**Python Patterns:**
- Prefixed log lines with source in brackets: `print(f"[{provider.name}] Error: {e}")`, `print("[Report] Email sent to ...")`
- `rich.console.Console` used exclusively in CLI (`homesearch/main.py`) for styled output
- No structured logging (`logging` module not used anywhere)

**JavaScript Patterns:**
- `console.error()` for caught exceptions only
- No `console.log()` in production paths

## Comments

**Python Docstrings:**
- Module-level docstrings on every `.py` file describing purpose: `"""FastAPI REST API for the web frontend."""`
- Class docstrings on Pydantic models: `"""All possible search filters. Every field is optional."""`
- Function docstrings on public functions; private helpers (`_safe_float`, `_row_to_listing`) have no docstrings
- Inline comments used liberally for section headers: `# 1. Listing type`, `# Rate limiting - be respectful`

**JavaScript Comments:**
- JSX block comments (`{/* ... */}`) used as section dividers within JSX: `{/* Location + Radius */}`
- Inline `//` comments for logic clarification

## Function Design

**Size:**
- Python: Most functions under 40 lines. `search_interactive()` in `homesearch/main.py` is ~130 lines (intentionally long CLI wizard)
- JSX: Components under 200 lines; `SearchForm` is the longest at ~395 lines due to inline JSX

**Parameters:**
- Pydantic models used for multi-field inputs (`SearchCriteria`, `SearchRequest`)
- `**kwargs` used in `database.update_search()` for dynamic SQL updates
- Optional parameters use `Optional[T] = None` annotation (Python) or `= false` / `= null` defaults (JS)

**Return Values:**
- Python functions return typed values: `list[Listing]`, `list[SavedSearch]`, `Optional[SavedSearch]`, `bool`, `int`
- Functions that can find nothing return `[]` or `None` (never raise)
- Boolean success pattern used for side-effect operations: `send_email_report()` returns `True/False`

## Module Design

**Python Exports:**
- No `__all__` defined in any module
- Public API implied by naming (`_` prefix = private)
- `homesearch/__init__.py` is empty (package marker only)
- `homesearch/providers/__init__.py` is empty (package marker only)
- `homesearch/services/__init__.py` is empty (package marker only)

**JavaScript Exports:**
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

---

*Convention analysis: 2026-03-25*
