---
phase: 01-interactive-cli-core
plan: "01"
subsystem: api
tags: [fastapi, lifespan, questionary, art, rich, tui, python]

# Dependency graph
requires: []
provides:
  - FastAPI app with lifespan context manager replacing deprecated on_event
  - homesearch/tui/ package with shared HOUSE_STYLE and Rich console
  - questionary and art declared as project dependencies
  - homerfindr CLI entry point alias
  - pytest testpaths configuration
affects: [02-interactive-cli-core, 03-interactive-cli-core, 04-interactive-cli-core]

# Tech tracking
tech-stack:
  added: [questionary>=2.1.1, art>=6.5]
  patterns:
    - asynccontextmanager lifespan pattern for FastAPI startup/shutdown
    - Shared TUI console/styles module for all TUI submodules to import from

key-files:
  created:
    - homesearch/tui/__init__.py
    - homesearch/tui/styles.py
  modified:
    - homesearch/api/routes.py
    - pyproject.toml

key-decisions:
  - "Use asynccontextmanager lifespan instead of on_event (eliminates DeprecationWarning that corrupts Rich output)"
  - "Centralize questionary Style and Rich Console in homesearch/tui/styles.py as single source of truth for all TUI modules"

patterns-established:
  - "Lifespan pattern: all FastAPI startup/shutdown logic goes in @asynccontextmanager lifespan(app) function"
  - "TUI imports: all TUI modules import HOUSE_STYLE, console, and COLOR_* constants from homesearch.tui.styles"

requirements-completed: [FIX-02]

# Metrics
duration: 3min
completed: "2026-03-25"
---

# Phase 01 Plan 01: Foundation and FastAPI Deprecation Fix Summary

**FastAPI lifespan context manager replacing deprecated on_event, questionary/art deps added, and homesearch/tui/ package with shared green/cyan HOUSE_STYLE and Rich console constants**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T21:45:14Z
- **Completed:** 2026-03-25T21:48:16Z
- **Tasks:** 2
- **Files modified:** 4 (2 modified, 2 created)

## Accomplishments

- Fixed FIX-02: replaced deprecated `@app.on_event("startup")` with `@asynccontextmanager async def lifespan()` — FastAPI now imports with zero DeprecationWarnings
- Added `questionary>=2.1.1` and `art>=6.5` to pyproject.toml dependencies; added `homerfindr` entry point alias and pytest testpaths config
- Created `homesearch/tui/` package with `styles.py` exporting `HOUSE_STYLE`, `console`, and 8 Rich `COLOR_*` constants for consistent TUI styling across all Plans 02-04

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix FastAPI lifespan deprecation and add dependencies** - `7887810` (fix)
2. **Task 2: Create TUI package skeleton with shared styles** - `d60a909` (feat)

**Plan metadata:** (docs commit — see state update commit)

## Files Created/Modified

- `homesearch/api/routes.py` - Added asynccontextmanager lifespan, removed on_event startup handler
- `pyproject.toml` - Added questionary/art deps, homerfindr entry point, pytest testpaths, fixed redfin version and build backend
- `homesearch/tui/__init__.py` - Empty package marker
- `homesearch/tui/styles.py` - HOUSE_STYLE questionary Style, shared Console, 8 Rich color constants

## Decisions Made

- Centralizing all questionary and Rich style constants in `homesearch/tui/styles.py` — single import source prevents style drift across splash, menu, wizard, and results modules
- Used `asynccontextmanager` pattern over class-based lifespan (simpler, idiomatic for single startup call)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed invalid redfin dependency version**
- **Found during:** Task 1 (dependency resolution)
- **Issue:** `redfin>=0.2.0` in pyproject.toml but PyPI only has redfin up to 0.1.1 — caused `uv run` to fail with "unsatisfiable requirements"
- **Fix:** Changed to `redfin>=0.1.0`
- **Files modified:** pyproject.toml
- **Verification:** `uv run python` resolved successfully
- **Committed in:** 7887810 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed invalid build-backend in pyproject.toml**
- **Found during:** Task 1 (package build during uv sync)
- **Issue:** `setuptools.backends._legacy:_Backend` is not a valid build backend for the installed setuptools version — caused ModuleNotFoundError on build
- **Fix:** Changed to standard `setuptools.build_meta`
- **Files modified:** pyproject.toml
- **Verification:** `uv run python -W error::DeprecationWarning -c "from homesearch.api.routes import app"` exits 0
- **Committed in:** 7887810 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - pre-existing bugs in pyproject.toml)
**Impact on plan:** Both fixes essential for the project to build and run at all. No scope creep.

## Issues Encountered

None beyond the two pre-existing pyproject.toml bugs documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- FIX-02 resolved: Rich terminal output is now clean (no deprecation warning corruption)
- `homesearch.tui.styles` is ready for import — Plans 02-04 can use `HOUSE_STYLE`, `console`, and `COLOR_*` constants immediately
- `questionary` and `art` are declared dependencies; will be available after `pip install -e .`
- No blockers for Plans 02, 03, or 04

---
*Phase: 01-interactive-cli-core*
*Completed: 2026-03-25*
