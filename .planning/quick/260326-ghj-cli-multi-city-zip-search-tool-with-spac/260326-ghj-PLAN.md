---
phase: quick
plan: 260326-ghj
type: execute
wave: 1
depends_on: []
files_modified:
  - homesearch/tui/zip_browser.py
  - homesearch/tui/wizard.py
autonomous: true
must_haves:
  truths:
    - "User can choose between single-area and multi-area search modes"
    - "User can add multiple cities one by one in multi-area mode"
    - "User sees a grouped ZIP browser with spacebar select/deselect for each location"
    - "All selected ZIPs across all locations merge into one deduped list"
    - "Summary shows total ZIP count and area names before search runs"
  artifacts:
    - path: "homesearch/tui/zip_browser.py"
      provides: "ZIP browser with questionary.checkbox grouped by city"
      exports: ["show_zip_browser"]
    - path: "homesearch/tui/wizard.py"
      provides: "Multi-location entry loop and zip browser integration"
  key_links:
    - from: "homesearch/tui/zip_browser.py"
      to: "homesearch/services/zip_service.py"
      via: "calls discover_zip_codes()"
      pattern: "discover_zip_codes"
    - from: "homesearch/tui/wizard.py"
      to: "homesearch/tui/zip_browser.py"
      via: "calls show_zip_browser() for each location"
      pattern: "show_zip_browser"
---

<objective>
Add multi-city ZIP search with interactive ZIP browser to the CLI wizard.

Purpose: Let users search multiple metro areas at once (e.g., Austin + Round Rock + Cedar Park) with fine-grained ZIP selection via spacebar toggle, replacing the silent auto-selection.
Output: New `zip_browser.py` module + updated wizard flow with single/multi mode choice.
</objective>

<context>
@homesearch/tui/wizard.py
@homesearch/services/zip_service.py
@homesearch/models.py
@homesearch/tui/styles.py
</context>

<interfaces>
From homesearch/services/zip_service.py:
```python
def discover_zip_codes(location: str, radius_miles: int = 25) -> list[ZipInfo]:
```

From homesearch/models.py:
```python
class ZipInfo(BaseModel):
    zipcode: str
    city: str
    state: str
    latitude: float
    longitude: float
    population: Optional[int] = None

class SearchCriteria(BaseModel):
    location: str = ""
    radius_miles: int = 25
    zip_codes: list[str] = Field(default_factory=list)
    excluded_zips: list[str] = Field(default_factory=list)
    # ... rest of fields
```

From homesearch/tui/styles.py:
```python
HOUSE_STYLE  # questionary Style object
console      # rich.console.Console instance
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create ZIP browser module</name>
  <files>homesearch/tui/zip_browser.py</files>
  <action>
Create `homesearch/tui/zip_browser.py` with a single public function:

```python
def show_zip_browser(location: str, radius_miles: int) -> list[str] | None:
```

Implementation:
1. Call `discover_zip_codes(location, radius_miles)` to get `list[ZipInfo]`.
2. If no ZIPs found, print yellow warning and return empty list.
3. Group ZIPs by city name using a dict: `{"Austin": [ZipInfo, ...], "Round Rock": [...]}`. Sort groups alphabetically by city name.
4. Build `questionary.checkbox` choices list:
   - For each city group, add a `questionary.Separator(f"--- {city}, {state} ---")` line.
   - For each ZIP in that group, add a `questionary.Choice(title=f"{z.zipcode} -- {z.city} (pop: {z.population:,})", value=z.zipcode, checked=True)` where population defaults to "N/A" if None.
   - Cap total ZIPs at 100 (take top 100 by population before grouping) to keep the list navigable.
5. Show the checkbox with prompt "Select ZIP codes (Space=toggle, Enter=confirm):" using `HOUSE_STYLE`.
6. If user cancels (returns None from questionary), return None.
7. Return the list of selected ZIP code strings.

Import `questionary` (including `Separator` and `Choice` from `questionary`), `discover_zip_codes` from zip_service, `ZipInfo` from models, `HOUSE_STYLE` and `console` from styles. Add module docstring following project convention.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "from homesearch.tui.zip_browser import show_zip_browser; print('Import OK')"</automated>
  </verify>
  <done>show_zip_browser function exists, imports cleanly, accepts (location, radius_miles) and returns list[str] | None</done>
</task>

<task type="auto">
  <name>Task 2: Add multi-location mode and ZIP browser to wizard</name>
  <files>homesearch/tui/wizard.py</files>
  <action>
Modify `_run_wizard_once()` in `homesearch/tui/wizard.py`. The changes go in two places:

**A. Replace section 3 (Location) and section 5 (ZIP Discovery) — lines ~258-304:**

After section 2 (Property Type), replace the location + radius + ZIP discovery sections with:

1. Ask search mode via `questionary.select`:
   - Prompt: "Search mode:"
   - Choices: ["Single area", "Multiple areas (pinpointed)"]
   - Use HOUSE_STYLE. Return None on cancel.

2. Ask radius (same as current section 4, keep as-is).

3. **If single area:**
   - Ask location via `questionary.text` (same as current section 3).
   - Import and call `show_zip_browser(location, radius_miles)` from `homesearch.tui.zip_browser`.
   - If show_zip_browser returns None, return None (cancelled).
   - Set `zip_codes` to the returned list.
   - Set `location` to the entered location string.
   - Set `excluded_zips = []`.

4. **If multiple areas:**
   - Initialize `all_locations: list[str] = []` and `all_zips: list[str] = []`.
   - Enter a loop:
     a. Ask location via `questionary.text` ("City, State or ZIP code:", HOUSE_STYLE). Return None on cancel.
     b. Add to `all_locations`.
     c. Call `show_zip_browser(location_input, radius_miles)`. If returns None, return None.
     d. Extend `all_zips` with returned ZIPs.
     e. Ask `questionary.confirm("Add another location?", default=False, style=HOUSE_STYLE)`. If None, return None. If False, break loop.
   - Dedupe: `zip_codes = list(dict.fromkeys(all_zips))` (preserves order).
   - Set `location` to `all_locations[0]` (first city, for SearchCriteria compatibility).
   - Print summary: `console.print(f"[green]Selected {len(zip_codes)} ZIP codes across {len(all_locations)} areas: {', '.join(all_locations)}[/green]")`
   - Set `excluded_zips = []`.

**B. Move radius question BEFORE location** so it applies to all ZIP browser calls. Currently radius is section 4 (after location). Move it to come right after property type (section 2), before the search mode question. This way radius_miles is available for both single and multi-area flows.

**C. Add import** at top of `_run_wizard_once`: `from homesearch.tui.zip_browser import show_zip_browser` (lazy import inside function, matching existing pattern for discover_zip_codes).

Keep all other wizard sections (6-19: price, beds, baths, etc.) exactly as they are.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "from homesearch.tui.wizard import run_search_wizard; print('Import OK')"</automated>
  </verify>
  <done>Wizard offers single/multi mode, multi mode loops for cities, ZIP browser shown for each location, merged deduped ZIPs passed to SearchCriteria, summary printed</done>
</task>

</tasks>

<verification>
- `python -c "from homesearch.tui.zip_browser import show_zip_browser"` imports without error
- `python -c "from homesearch.tui.wizard import run_search_wizard"` imports without error
- Manual test: run `homesearch search`, select "Multiple areas", enter two cities, confirm ZIP selections merge correctly
</verification>

<success_criteria>
- ZIP browser module exists with grouped checkbox UI using questionary.Separator
- Wizard offers single vs multi-area choice after property type
- Multi-area mode loops for city entry with "Add another?" confirmation
- Each location shows ZIP browser for fine-grained selection
- All ZIPs merge deduped into SearchCriteria.zip_codes
- Summary line shows ZIP count and area names
- Single-area mode also shows ZIP browser (replacing silent auto-selection)
</success_criteria>

<output>
After completion, create `.planning/quick/260326-ghj-cli-multi-city-zip-search-tool-with-spac/260326-ghj-SUMMARY.md`
</output>
