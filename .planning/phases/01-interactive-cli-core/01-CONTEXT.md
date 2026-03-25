# Phase 1: Interactive CLI Core - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current typing-based Typer CLI with a fully interactive arrow-key experience. Users can launch HomerFindr, see a house-themed ASCII splash screen, navigate a colorful main menu, run the full 15-field search wizard, and view results — all with arrows + Enter only (except city/ZIP entry). Fix FastAPI deprecation warnings that would corrupt Rich output.

</domain>

<decisions>
## Implementation Decisions

### Splash Screen
- **D-01:** Large ASCII art house with "HomerFindr" title rendered via `art` library (677+ fonts), colored with Rich gradient (green → cyan)
- **D-02:** Typewriter-style reveal animation (Rich Live context), displays for ~2 seconds, then clears to main menu
- **D-03:** Splash shows on every launch — it's the brand moment, keep it fast enough to not annoy

### Menu Navigation
- **D-04:** Arrow pointer (►) with highlighted/inverted background for selected item — questionary select prompts
- **D-05:** Green/cyan accent colors on dark terminal background — consistent house theme throughout
- **D-06:** Main menu options in order: 🏠 New Search, 📋 Saved Searches, ⚙️ Settings, 🌐 Launch Web UI, 🚪 Exit
- **D-07:** After any action completes, return to main menu (loop until Exit or Ctrl+C)

### Search Wizard
- **D-08:** City/State or ZIP code is the ONLY field requiring keyboard typing — everything else is arrow-selectable
- **D-09:** Field order follows the existing wizard: Type → Property → Location → Radius → ZIP Discovery → Price → Beds → Baths → Sqft → Lot → Year → Floors → Basement → Garage → HOA
- **D-10:** Each optional field shows "(Enter to skip)" hint — pressing Enter with no selection skips the field
- **D-11:** Price, sqft, lot size use pre-built range options (e.g., "$200k-$300k", "$300k-$400k") not free typing
- **D-12:** At the end of wizard, show search summary panel and confirm: "Search now?" (Yes/No/Edit)

### Results Display
- **D-13:** Rich table with colored columns: Price (green), Beds/Baths (cyan), Sqft (yellow), Address (white)
- **D-14:** Results count header: "Found 47 listings across 2 providers"
- **D-15:** Arrow keys to scroll through results, Enter on a row opens the listing URL in default browser
- **D-16:** After viewing results: "Save this search?" prompt, then return to main menu

### Search Execution
- **D-17:** Search runs on a background thread (threading.Thread) so Rich spinner stays animated
- **D-18:** Rich spinner with house emoji: "🏠 Searching Realtor.com..." then "🏠 Searching Redfin..."
- **D-19:** If a provider fails/403s, show warning but continue with other providers' results

### Claude's Discretion
- Exact ASCII art font choice (from art library's 677+ options)
- Spinner animation style (dots, line, bounce — whatever looks best with Rich)
- Exact color hex values within the green/cyan theme
- Table column widths and truncation behavior
- Error message wording

</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above and in:

### Project context
- `.planning/PROJECT.md` — Core value, constraints, target users
- `.planning/REQUIREMENTS.md` — FIX-02, CLI-01 through CLI-09 acceptance criteria

### Research
- `.planning/research/STACK.md` — questionary vs InquirerPy decision, art library recommendation
- `.planning/research/ARCHITECTURE.md` — CLI layer architecture, Rich + menu library sequencing
- `.planning/research/PITFALLS.md` — Rich/menu conflict warning, blocking search thread issue

### Existing code
- `homesearch/main.py` — Current Typer CLI entry point to replace
- `homesearch/services/search_service.py` — SearchService.search() to call from wizard
- `homesearch/models.py` — SearchCriteria and Listing models

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `homesearch/services/search_service.py`: SearchService with `search(criteria)` and `get_providers()` — reuse directly from new interactive wizard
- `homesearch/models.py`: SearchCriteria dataclass with all 15 fields — wizard populates this same model
- `homesearch/database.py`: SavedSearchDB with save/load/list/delete — reuse for "Save this search?" flow
- `homesearch/services/zip_service.py`: ZipCodeService for radius ZIP discovery — reuse in wizard

### Established Patterns
- Typer app with `@app.command()` decorators — replace with questionary-driven menu loop
- Rich console already imported and used for basic output — extend with Live, Spinner, Table
- Provider pattern (BaseProvider → homeharvest, redfin) — no changes needed, just call SearchService

### Integration Points
- `homesearch/main.py` entry point — rewire from Typer commands to interactive menu loop
- `pyproject.toml` `[project.scripts]` — already has `homesearch` entry point, add `homerfindr` alias
- FastAPI deprecation fix (FIX-02) — migrate `on_event` to lifespan context manager in `homesearch/api/routes.py`

</code_context>

<specifics>
## Specific Ideas

- User wants it to feel fun and colorful — not a boring terminal app
- ASCII house theme should be memorable — first impression matters
- "Don't forget to make it streamlined" — wizard should feel fast, not tedious
- Zero typing is the north star — city/ZIP is the only exception
- References to tools like lazygit and btop for CLI navigation feel

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-interactive-cli-core*
*Context gathered: 2026-03-25*
