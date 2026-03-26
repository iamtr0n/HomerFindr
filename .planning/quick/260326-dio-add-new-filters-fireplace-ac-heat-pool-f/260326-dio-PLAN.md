---
phase: quick
plan: 260326-dio
type: execute
wave: 1
depends_on: []
files_modified:
  - homesearch/models.py
  - homesearch/tui/wizard.py
  - homesearch/providers/homeharvest_provider.py
  - homesearch/providers/redfin_provider.py
  - homesearch/services/search_service.py
  - homesearch/services/zip_service.py
  - homesearch/database.py
  - homesearch/services/scheduler_service.py
  - homesearch/api/routes.py
  - frontend/src/components/SearchForm.jsx
autonomous: true
must_haves:
  truths:
    - "Searching with fireplace/AC/heat/pool filters returns only matching listings"
    - "Typing 'Austin TX' or 'Austin Texas' (no comma) discovers ZIP codes correctly"
    - "Coming Soon listing type is available in wizard and returns pre-market listings"
    - "Real-time alert job runs every 10 minutes and notifies on new listings"
  artifacts:
    - path: "homesearch/models.py"
      provides: "New filter fields on SearchCriteria and Listing, COMING_SOON enum value"
      contains: "has_fireplace"
    - path: "homesearch/services/zip_service.py"
      provides: "Bare city+state parsing without comma"
      contains: "_parse_state"
    - path: "homesearch/services/scheduler_service.py"
      provides: "High-frequency alert job"
      contains: "alert"
  key_links:
    - from: "homesearch/providers/homeharvest_provider.py"
      to: "homesearch/models.py"
      via: "description keyword detection for fireplace/AC/heat/pool"
      pattern: "has_fireplace|has_ac|heat_type|has_pool"
    - from: "homesearch/services/search_service.py"
      to: "homesearch/models.py"
      via: "_passes_filters checks new criteria fields"
      pattern: "has_fireplace|has_ac|has_pool"
---

<objective>
Add four new search filters (fireplace, AC, heat type, pool), fix ZIP discovery for bare city names without commas, add Coming Soon pre-market listing type, and implement real-time saved search alerts with desktop notifications.

Purpose: Expand filter coverage for house-hunting must-haves, fix a usability bug in location entry, unlock pre-market listings, and enable instant new-listing alerts.
Output: Updated models, providers, wizard, filters, ZIP parser, scheduler with alert job.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@homesearch/models.py
@homesearch/tui/wizard.py
@homesearch/providers/homeharvest_provider.py
@homesearch/providers/redfin_provider.py
@homesearch/services/search_service.py
@homesearch/services/zip_service.py
@homesearch/database.py
@homesearch/services/scheduler_service.py

<interfaces>
From homesearch/models.py:
```python
class ListingType(str, Enum):
    SALE = "sale"
    RENT = "rent"
    SOLD = "sold"

class SearchCriteria(BaseModel):
    # ... existing fields ...
    has_basement: Optional[bool] = None
    has_garage: Optional[bool] = None
    garage_spaces_min: Optional[int] = None
    hoa_max: Optional[float] = None

class Listing(BaseModel):
    # ... existing fields ...
    has_garage: Optional[bool] = None
    garage_spaces: Optional[int] = None
    has_basement: Optional[bool] = None
```

From homesearch/services/search_service.py:
```python
def _passes_filters(listing: Listing, criteria: SearchCriteria) -> bool:
    # Client-side filtering for fields providers might not support natively
```

From homesearch/providers/homeharvest_provider.py:
```python
_LISTING_TYPE_MAP = {
    ListingType.SALE: "for_sale",
    ListingType.RENT: "for_rent",
    ListingType.SOLD: "sold",
}
# Garage/basement detection from description:
desc = str(_coalesce(row.get("description"), row.get("text")) or "").lower()
```

From homesearch/services/zip_service.py:
```python
def _parse_city(location: str) -> str:
    parts = location.split(",")
    return parts[0].strip()

def _parse_state(location: str) -> str:
    parts = location.split(",")
    if len(parts) >= 2:
        return parts[1].strip()
    return ""
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add new filter fields, Coming Soon enum, ZIP fix, and DB migration</name>
  <files>homesearch/models.py, homesearch/services/zip_service.py, homesearch/database.py</files>
  <action>
**models.py — New enum value and fields:**

1. Add `COMING_SOON = "coming_soon"` to `ListingType` enum after `SOLD`.

2. Add these fields to `SearchCriteria` after `hoa_max`:
```python
has_fireplace: Optional[bool] = None
has_ac: Optional[bool] = None
heat_type: Optional[str] = None  # "any", "gas", "electric", "radiant", None
has_pool: Optional[bool] = None
```

3. Add these fields to `Listing` after `has_basement` (line ~83):
```python
has_fireplace: Optional[bool] = None
has_ac: Optional[bool] = None
heat_type: Optional[str] = None  # Detected: "gas", "electric", "radiant", "forced air", etc.
has_pool: Optional[bool] = None
```

**zip_service.py — Fix bare city name parsing:**

Replace `_parse_city` and `_parse_state` with smarter versions that handle three formats:
- "Austin, TX" (existing comma format — works today)
- "Austin TX" (space-separated, last token is 2-letter state abbreviation)
- "Austin Texas" (space-separated, last token is full state name)

Implementation:
```python
# Full state name -> abbreviation mapping (all 50 states + DC)
_STATE_ABBREVS = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
_ABBREV_SET = set(_STATE_ABBREVS.values())  # {"AL", "AK", ...}

def _parse_city(location: str) -> str:
    """Extract city from 'City, State' or 'City State' format."""
    if "," in location:
        return location.split(",")[0].strip()
    tokens = location.strip().split()
    if len(tokens) >= 2:
        last = tokens[-1]
        # Check if last token is a 2-letter abbreviation
        if last.upper() in _ABBREV_SET:
            return " ".join(tokens[:-1])
        # Check if last token(s) form a full state name
        for n in (2, 1):  # Try 2-word states first ("New York"), then 1-word
            if len(tokens) > n:
                candidate = " ".join(tokens[-n:]).lower()
                if candidate in _STATE_ABBREVS:
                    return " ".join(tokens[:-n])
    return location.strip()

def _parse_state(location: str) -> str:
    """Extract state from 'City, State' or 'City State' format."""
    if "," in location:
        parts = location.split(",")
        return parts[1].strip() if len(parts) >= 2 else ""
    tokens = location.strip().split()
    if len(tokens) >= 2:
        last = tokens[-1]
        if last.upper() in _ABBREV_SET:
            return last.upper()
        for n in (2, 1):
            if len(tokens) > n:
                candidate = " ".join(tokens[-n:]).lower()
                if candidate in _STATE_ABBREVS:
                    return _STATE_ABBREVS[candidate]
    return ""
```

**database.py — Schema migration for new columns:**

Add a migration function called after `init_db()`. After `conn.executescript(SCHEMA)` in `init_db()`, add calls to safely add new columns if they don't exist:
```python
# Add new filter columns (safe — ALTER TABLE ADD COLUMN is a no-op if column exists in SQLite when wrapped in try/except)
for col, col_type in [
    ("has_fireplace", "INTEGER"),
    ("has_ac", "INTEGER"),
    ("heat_type", "TEXT"),
    ("has_pool", "INTEGER"),
]:
    try:
        conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {col_type}")
    except Exception:
        pass  # Column already exists
```

Update `upsert_listing()`: Add the 4 new fields to the INSERT column list and values tuple, following the same pattern as `has_garage`/`has_basement` (use `int(listing.has_X) if listing.has_X is not None else None` for booleans, direct value for `heat_type`).

Update `_row_to_listing()`: Map the 4 new DB columns to `Listing` fields, same pattern as `has_garage`/`has_basement`.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "
from homesearch.models import ListingType, SearchCriteria, Listing
assert hasattr(ListingType, 'COMING_SOON'), 'Missing COMING_SOON'
c = SearchCriteria(has_fireplace=True, has_ac=True, heat_type='gas', has_pool=True)
assert c.has_fireplace is True
l = Listing(source='test', source_id='1', address='123 Main', has_fireplace=True, has_pool=True)
assert l.has_fireplace is True
from homesearch.services.zip_service import _parse_city, _parse_state
assert _parse_city('Austin TX') == 'Austin', f'Got {_parse_city(\"Austin TX\")}'
assert _parse_state('Austin TX') == 'TX', f'Got {_parse_state(\"Austin TX\")}'
assert _parse_city('Austin, TX') == 'Austin'
assert _parse_state('Austin, TX') == 'TX'
assert _parse_city('New York NY') == 'New York'
assert _parse_state('San Antonio Texas') == 'TX'
print('All model + ZIP checks passed')
"</automated>
  </verify>
  <done>ListingType has COMING_SOON value. SearchCriteria and Listing have has_fireplace, has_ac, heat_type, has_pool fields. ZIP parser handles "City ST", "City State", and "City, State" formats. DB schema adds new columns on init.</done>
</task>

<task type="auto">
  <name>Task 2: Wire new filters into providers, wizard, search filter, and Coming Soon support</name>
  <files>homesearch/providers/homeharvest_provider.py, homesearch/providers/redfin_provider.py, homesearch/tui/wizard.py, homesearch/services/search_service.py</files>
  <action>
**homeharvest_provider.py — Description detection + Coming Soon:**

1. Add `COMING_SOON` to `_LISTING_TYPE_MAP`:
```python
ListingType.COMING_SOON: "coming_soon",
```

2. In the `_row_to_listing` method, after the garage/basement detection block (around line 128-129), add detection for the 4 new features using the existing `desc` variable:
```python
has_fireplace = True if "fireplace" in desc else None
has_ac = None
if "central air" in desc or "central a/c" in desc or "central ac" in desc:
    has_ac = True
elif "window unit" in desc or "no a/c" in desc or "no ac" in desc or "no air" in desc:
    has_ac = False
heat_type = None
if "gas heat" in desc or "natural gas" in desc or "gas furnace" in desc:
    heat_type = "gas"
elif "electric heat" in desc or "electric furnace" in desc or "heat pump" in desc:
    heat_type = "electric"
elif "radiant" in desc:
    heat_type = "radiant"
elif "forced air" in desc:
    heat_type = "forced air"
has_pool = True if ("pool" in desc and "pool table" not in desc and "carpool" not in desc) else None
```

3. Pass `has_fireplace=has_fireplace, has_ac=has_ac, heat_type=heat_type, has_pool=has_pool` to the `Listing(...)` constructor.

**redfin_provider.py — Coming Soon + listing type:**

1. In `_get_listing_type_num`, add: `if criteria.listing_type == ListingType.COMING_SOON: return 4` (Redfin uses 4 for coming soon — if this doesn't work, return 1 as fallback; Redfin may not support coming soon natively).

2. In the listing_type string assignment block, add: `elif criteria.listing_type == ListingType.COMING_SOON: lt = "coming_soon"`.

**wizard.py — New filter questions:**

1. Add "Coming Soon" to the listing type choices (after "Sold"). Map it: `"Coming Soon": ListingType.COMING_SOON`.

2. After the garage spaces question block (around line 427) and before the HOA section (line 431), add 4 new questions following the exact same pattern as basement/garage:

```python
# Step: Fireplace
fireplace_answer = questionary.select(
    "Fireplace:",
    choices=["Don't care", "Must have", "No fireplace"],
    style=HOUSE_STYLE,
    qmark=HOUSE_ICON,
).ask()
if fireplace_answer is None:
    return None
fireplace_map = {"Must have": True, "No fireplace": False, "Don't care": None}
has_fireplace = fireplace_map[fireplace_answer]

# Step: Air Conditioning
ac_answer = questionary.select(
    "Air Conditioning:",
    choices=["Don't care", "Must have", "No AC"],
    style=HOUSE_STYLE,
    qmark=HOUSE_ICON,
).ask()
if ac_answer is None:
    return None
ac_map = {"Must have": True, "No AC": False, "Don't care": None}
has_ac = ac_map[ac_answer]

# Step: Heat Type
heat_answer = questionary.select(
    "Heat type:",
    choices=["Don't care", "Gas", "Electric", "Radiant", "Forced Air"],
    style=HOUSE_STYLE,
    qmark=HOUSE_ICON,
).ask()
if heat_answer is None:
    return None
heat_type = None if heat_answer == "Don't care" else heat_answer.lower()

# Step: Pool
pool_answer = questionary.select(
    "Pool:",
    choices=["Don't care", "Must have", "No pool"],
    style=HOUSE_STYLE,
    qmark=HOUSE_ICON,
).ask()
if pool_answer is None:
    return None
pool_map = {"Must have": True, "No pool": False, "Don't care": None}
has_pool = pool_map[pool_answer]
```

3. Pass `has_fireplace=has_fireplace, has_ac=has_ac, heat_type=heat_type, has_pool=has_pool` to the `SearchCriteria(...)` constructor at the end of the wizard.

4. In the summary table display function, add rows for the new fields (after garage, before HOA):
```python
if criteria.has_fireplace is not None:
    table.add_row("Fireplace", "Required" if criteria.has_fireplace else "No fireplace")
if criteria.has_ac is not None:
    table.add_row("AC", "Required" if criteria.has_ac else "No AC")
if criteria.heat_type is not None:
    table.add_row("Heat type", criteria.heat_type.title())
if criteria.has_pool is not None:
    table.add_row("Pool", "Required" if criteria.has_pool else "No pool")
```

**search_service.py — Extend _passes_filters:**

After the `hoa_max` check (line 186-187) and before the `property_types` check, add:
```python
if criteria.has_fireplace is True and listing.has_fireplace is not True:
    return False

if criteria.has_ac is True and listing.has_ac is not True:
    return False
if criteria.has_ac is False and listing.has_ac is True:
    return False

if criteria.heat_type and criteria.heat_type != "any":
    if listing.heat_type and listing.heat_type != criteria.heat_type:
        return False

if criteria.has_pool is True and listing.has_pool is not True:
    return False
if criteria.has_pool is False and listing.has_pool is True:
    return False
```

Note: For `has_fireplace`, only filter OUT if user requires it (`True`) but listing doesn't have it. We don't filter out listings with fireplaces when user says "no fireplace" — that would be unusual. Same soft approach for pool in the negative case is fine since pool_map includes "No pool" as an option.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "
from homesearch.models import Listing, SearchCriteria, ListingType
from homesearch.services.search_service import _passes_filters

# Test fireplace filter
c = SearchCriteria(has_fireplace=True)
l_yes = Listing(source='t', source_id='1', address='a', has_fireplace=True)
l_no = Listing(source='t', source_id='2', address='b', has_fireplace=None)
assert _passes_filters(l_yes, c) is True
assert _passes_filters(l_no, c) is False

# Test pool filter
c2 = SearchCriteria(has_pool=True)
l_pool = Listing(source='t', source_id='3', address='c', has_pool=True)
l_nopool = Listing(source='t', source_id='4', address='d', has_pool=None)
assert _passes_filters(l_pool, c2) is True
assert _passes_filters(l_nopool, c2) is False

# Test heat_type filter
c3 = SearchCriteria(heat_type='gas')
l_gas = Listing(source='t', source_id='5', address='e', heat_type='gas')
l_elec = Listing(source='t', source_id='6', address='f', heat_type='electric')
l_unk = Listing(source='t', source_id='7', address='g', heat_type=None)
assert _passes_filters(l_gas, c3) is True
assert _passes_filters(l_elec, c3) is False
assert _passes_filters(l_unk, c3) is True  # Unknown passes (don't exclude)

# Test Coming Soon enum
assert ListingType.COMING_SOON.value == 'coming_soon'

# Test homeharvest map
from homesearch.providers.homeharvest_provider import _LISTING_TYPE_MAP
assert _LISTING_TYPE_MAP[ListingType.COMING_SOON] == 'coming_soon'

print('All filter + Coming Soon checks passed')
"</automated>
  </verify>
  <done>Wizard presents fireplace/AC/heat/pool questions and Coming Soon listing type. Providers detect features from descriptions. _passes_filters enforces all new criteria. Coming Soon works end-to-end through homeharvest.</done>
</task>

<task type="auto">
  <name>Task 3: Implement real-time saved search alert job with desktop notifications</name>
  <files>homesearch/services/scheduler_service.py, homesearch/services/search_service.py</files>
  <action>
**scheduler_service.py — Add high-frequency alert job:**

1. Import `IntervalTrigger` from apscheduler:
```python
from apscheduler.triggers.interval import IntervalTrigger
```

2. After the `daily_report_job` function definition inside `start_scheduler()`, add a new job function:

```python
def alert_job():
    """Check all active saved searches for new listings and send desktop notifications."""
    from homesearch import database as db
    from homesearch.services.search_service import run_search
    import subprocess
    import platform

    active_searches = db.get_saved_searches(active_only=True)
    if not active_searches:
        return

    for s in active_searches:
        try:
            previous_ids = set(db.get_previous_listing_ids(s.id))
            results = run_search(s.criteria, search_id=s.id)
            new_listings = [l for l in results if l.id and l.id not in previous_ids]

            if new_listings:
                count = len(new_listings)
                # Desktop notification via osascript (macOS)
                if platform.system() == "Darwin":
                    title = f"HomerFindr: {count} new listing{'s' if count > 1 else ''}"
                    # Show first listing address as body
                    body = new_listings[0].address
                    if count > 1:
                        body += f" and {count - 1} more"
                    body += f" ({s.name})"
                    subprocess.run([
                        "osascript", "-e",
                        f'display notification "{body}" with title "{title}" sound name "Glass"'
                    ], capture_output=True, timeout=5)
                print(f"[Alerts] {count} new listing(s) for '{s.name}'")
        except Exception as e:
            print(f"[Alerts] Error checking '{s.name}': {e}")
```

3. Register the alert job with a 10-minute interval, placed after the daily_report job registration:
```python
_scheduler.add_job(
    alert_job,
    trigger=IntervalTrigger(minutes=10),
    id="realtime_alerts",
    name="Real-time Listing Alerts",
    replace_existing=True,
)
print(f"[Scheduler] Real-time alerts running every 10 minutes")
```

**search_service.py — Ensure run_search returns listings with DB ids:**

Verify that `run_search` with a `search_id` parameter calls `db.upsert_listing(listing)` and the returned listing objects have their `id` field set. Looking at the current code (lines 92-101), `upsert_listing` returns the `lid` but it's NOT set back on the listing object. Fix this:

After `lid = db.upsert_listing(listing)` (line 96), add: `listing.id = lid`

This ensures the alert job can compare returned listing IDs against `previous_ids`.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "
from homesearch.services.scheduler_service import start_scheduler, stop_scheduler, _scheduler
# Verify scheduler can start and has both jobs
start_scheduler()
jobs = _scheduler.get_jobs()
job_ids = [j.id for j in jobs]
assert 'daily_report' in job_ids, f'Missing daily_report, got {job_ids}'
assert 'realtime_alerts' in job_ids, f'Missing realtime_alerts, got {job_ids}'
# Check interval
alert_job = next(j for j in jobs if j.id == 'realtime_alerts')
print(f'Alert trigger: {alert_job.trigger}')
stop_scheduler()
print('Scheduler alert job verified')
"</automated>
  </verify>
  <done>Scheduler runs an alert job every 10 minutes that checks all active saved searches, identifies new listings by comparing against previously seen source_ids, and sends macOS desktop notifications with listing details. Listing IDs are properly set after DB upsert so comparison works.</done>
</task>

</tasks>

<verification>
1. `python -c "from homesearch.models import *; print('Models OK')"` — imports clean
2. `python -c "from homesearch.services.zip_service import _parse_city, _parse_state; assert _parse_state('Austin TX') == 'TX'"` — ZIP fix works
3. `python -c "from homesearch.services.search_service import _passes_filters; print('Filters OK')"` — filter function loads
4. `python -c "from homesearch.services.scheduler_service import start_scheduler, stop_scheduler; start_scheduler(); stop_scheduler(); print('Scheduler OK')"` — both jobs register
</verification>

<success_criteria>
- SearchCriteria has has_fireplace, has_ac, heat_type, has_pool fields
- Listing model has matching fields; DB schema includes new columns
- Wizard presents 4 new questions after garage, before HOA
- ListingType.COMING_SOON exists and is wired through both providers
- _parse_state("Austin TX") returns "TX" and _parse_state("Austin Texas") returns "TX"
- _passes_filters enforces all new filter criteria
- Scheduler registers both daily_report and realtime_alerts jobs
- Alert job sends macOS desktop notification for new listings
</success_criteria>

<output>
After completion, create `.planning/quick/260326-dio-add-new-filters-fireplace-ac-heat-pool-f/260326-dio-SUMMARY.md`
</output>
