---
phase: quick
plan: 260326-gam
type: execute
wave: 1
depends_on: []
files_modified:
  - homesearch/models.py
  - homesearch/services/road_service.py
  - homesearch/services/school_service.py
  - homesearch/services/search_service.py
  - frontend/src/components/SearchForm.jsx
  - frontend/src/components/PropertyCard.jsx
  - frontend/src/pages/NewSearch.jsx
autonomous: true
requirements: [highway-proximity, school-ratings, organized-sections, form-additions]

must_haves:
  truths:
    - "Listings near highways are flagged and sorted last when avoid_highways is enabled"
    - "School ratings appear on listings that have zip_code data"
    - "Results are grouped into Perfect/Strong/Good/Near Highway sections"
    - "SearchForm has avoid_highways checkbox and school rating min select"
  artifacts:
    - path: "homesearch/services/road_service.py"
      provides: "Highway proximity detection via Overpass API"
      exports: ["check_highway_proximity"]
    - path: "homesearch/services/school_service.py"
      provides: "School rating lookup by zip code"
      exports: ["get_school_rating"]
    - path: "homesearch/models.py"
      provides: "Extended Listing and SearchCriteria with highway/school fields"
      contains: "near_highway"
    - path: "frontend/src/pages/NewSearch.jsx"
      provides: "Sectioned result display with collapsible groups"
  key_links:
    - from: "homesearch/services/search_service.py"
      to: "homesearch/services/road_service.py"
      via: "conditional call in run_search after filtering"
      pattern: "check_highway_proximity"
    - from: "homesearch/services/search_service.py"
      to: "homesearch/services/school_service.py"
      via: "call in run_search for each listing with zip_code"
      pattern: "get_school_rating"
    - from: "frontend/src/pages/NewSearch.jsx"
      to: "results.results"
      via: "groupBy logic splitting into match tiers"
      pattern: "Perfect Match|Strong Match|Good Options"
---

<objective>
Add highway proximity detection, school ratings, and organized result sections to HomerFindr.

Purpose: Give users richer listing intelligence -- avoid noisy highway-adjacent homes and surface school quality -- plus a cleaner results view grouped by match quality.
Output: Two new backend services (road_service.py, school_service.py), extended models, enriched search pipeline, sectioned frontend results, and new form controls.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@homesearch/models.py
@homesearch/services/search_service.py
@frontend/src/components/SearchForm.jsx
@frontend/src/components/PropertyCard.jsx
@frontend/src/pages/NewSearch.jsx
@homesearch/api/routes.py

<interfaces>
<!-- Key types and contracts the executor needs -->

From homesearch/models.py:
```python
class SearchCriteria(BaseModel):
    # ... existing fields ...
    has_pool: Optional[bool] = None

class Listing(BaseModel):
    # ... existing fields through has_pool ...
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_url: str = ""
    source_url: str = ""
```

From homesearch/services/search_service.py:
```python
def run_search(criteria, search_id=None, use_zip_discovery=True, errors=None, pre_filter_counts=None, on_progress=None) -> list[Listing]:
    # ... providers -> dedupe -> filter -> persist
    filtered = [l for l in deduped if _passes_filters(l, criteria)]
    return filtered

def _passes_filters(listing: Listing, criteria: SearchCriteria) -> bool:
    # Client-side filtering for fields providers might not support natively
```

From frontend/src/pages/NewSearch.jsx:
```javascript
// results shape from API: { results: Listing[], total: int, search_name: str, provider_errors: [] }
// sortedResults() returns [...results.results] sorted by sortBy state
```

From frontend/src/components/SearchForm.jsx:
```javascript
// Advanced filters section at line 294: <div className="space-y-4 mb-4 p-4 bg-gray-50 rounded-lg">
// Ends at line 393 with </div>
// Form submits criteria object matching SearchCriteria fields
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend services and model extensions</name>
  <files>
    homesearch/models.py,
    homesearch/services/road_service.py,
    homesearch/services/school_service.py,
    homesearch/services/search_service.py
  </files>
  <action>
**1a. Extend models (homesearch/models.py):**

Add to `SearchCriteria` (after `has_pool`):
```python
avoid_highways: bool = False
school_rating_min: Optional[int] = None  # 1-10
```

Add to `Listing` (after `has_pool` / before `year_built`):
```python
near_highway: bool = False
highway_name: str = ""
school_rating: Optional[int] = None  # 1-10
school_district: str = ""
```

**1b. Create road_service.py (homesearch/services/road_service.py):**

```python
"""Highway proximity detection using OpenStreetMap Overpass API."""

import requests

_cache: dict[tuple[float, float], tuple[bool, str]] = {}

def check_highway_proximity(lat: float, lon: float, radius_meters: int = 150) -> tuple[bool, str]:
    """Check if coordinates are near a major highway.

    Returns (is_near_highway, road_name). Fails gracefully to (False, "").
    """
```

- Build Overpass QL query: `[out:json][timeout:5];way(around:{radius_meters},{lat},{lon})[highway~"motorway|trunk|primary"];out tags 1;`
- POST to `https://overpass-api.de/api/interpreter` with `data=query`, timeout=5s
- Parse response JSON: if `elements` list is non-empty, extract first element's `tags.name` or `tags.ref` (e.g. "I-35")
- Cache in module-level `_cache` dict keyed by `(round(lat,4), round(lon,4))` to avoid repeat calls for nearby coords
- Wrap entire function in try/except: on any error, return `(False, "")`

**1c. Create school_service.py (homesearch/services/school_service.py):**

```python
"""School rating lookup using NCES/GreatSchools data."""

import requests

_cache: dict[str, tuple[int | None, str]] = {}

def get_school_rating(zip_code: str, city: str = "", state: str = "") -> tuple[int | None, str]:
    """Get approximate school rating for a location.

    Returns (rating_1_to_10, district_name). Returns (None, "") on failure.
    """
```

- PRACTICAL APPROACH: Use the free SchoolDigger API-like approach via web scraping is fragile. Instead, use Overpass API to find schools near the zip centroid, then use a simple heuristic:
  - Query Overpass for `node[amenity=school](area)` within the zip code
  - Count schools found as a density signal
  - Use the Niche.com or simply return a placeholder rating based on school count (more schools = better served area)

- SIMPLEST RELIABLE approach: Use `https://www.greatschools.org/search/search.zipcode?zip={zip_code}` with requests + basic HTML parsing to extract the summary rating (look for a rating number 1-10 in the response). Set a User-Agent header. Timeout 5s.

- If GreatSchools scraping fails or is blocked, fall back to returning `(None, "")` gracefully.

- Cache by zip_code in module-level `_cache` dict.

- Wrap entire function in try/except: on any error, return `(None, "")`.

**1d. Integrate into search_service.py:**

Add imports at top:
```python
from homesearch.services.road_service import check_highway_proximity
from homesearch.services.school_service import get_school_rating
```

In `run_search()`, AFTER the `filtered = [l for l in deduped if _passes_filters(...)]` line (line 91) and BEFORE the persist block (line 94), add:

```python
# Enrich: highway proximity (only when user opted in AND listing has coords)
if criteria.avoid_highways:
    for listing in filtered:
        if listing.latitude and listing.longitude:
            near, name = check_highway_proximity(listing.latitude, listing.longitude)
            listing.near_highway = near
            listing.highway_name = name

# Enrich: school ratings (for all listings with zip_code)
for listing in filtered:
    if listing.zip_code:
        rating, district = get_school_rating(listing.zip_code, listing.city, listing.state)
        listing.school_rating = rating
        listing.school_district = district
```

In `_passes_filters()`, add before the final `return True`:
```python
# School rating minimum
if criteria.school_rating_min and listing.school_rating and listing.school_rating < criteria.school_rating_min:
    return False
```

Note: school_rating filtering happens in _passes_filters BUT enrichment happens after filtering. This means school_rating_min filtering needs the enrichment to happen first. SOLUTION: Move the school enrichment BEFORE filtering, or do a two-pass approach. Best approach: enrich school ratings on the deduped list (before filtering), then filter including school_rating_min. Highway enrichment stays after filtering (it's display-only, not a filter).

Revised integration order in run_search():
1. After dedup (line 84): enrich school ratings on `deduped` list
2. Filter: `filtered = [l for l in deduped if _passes_filters(l, criteria)]` (school_rating_min now works)
3. After filter: enrich highway proximity on `filtered` list (only when avoid_highways=True)
4. After highway enrichment: sort so `near_highway=True` listings go to end:
```python
if criteria.avoid_highways:
    filtered.sort(key=lambda l: (l.near_highway, -(l.price or 0)))
```
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "
from homesearch.models import Listing, SearchCriteria
c = SearchCriteria(avoid_highways=True, school_rating_min=5)
assert c.avoid_highways is True
assert c.school_rating_min == 5
l = Listing(source='test', source_id='1', address='123 Main', near_highway=True, highway_name='I-35', school_rating=7, school_district='Austin ISD')
assert l.near_highway is True
assert l.school_rating == 7
from homesearch.services.road_service import check_highway_proximity
from homesearch.services.school_service import get_school_rating
print('All model and import checks pass')
"</automated>
  </verify>
  <done>
    - SearchCriteria has avoid_highways and school_rating_min fields
    - Listing has near_highway, highway_name, school_rating, school_district fields
    - road_service.py exists with check_highway_proximity that queries Overpass API, caches, and fails gracefully
    - school_service.py exists with get_school_rating that attempts rating lookup, caches, and fails gracefully
    - search_service.py enriches listings with school data before filtering, highway data after filtering
    - Highway-near listings sorted to end of results when avoid_highways is True
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend form controls and sectioned results</name>
  <files>
    frontend/src/components/SearchForm.jsx,
    frontend/src/components/PropertyCard.jsx,
    frontend/src/pages/NewSearch.jsx
  </files>
  <action>
**2a. SearchForm.jsx -- add two new controls in the advanced filters section:**

Inside the advanced filters `<div>` (after the HOA/Garage grid at ~line 392, before the closing `</div>` at line 393), add a new grid row:

```jsx
{/* Highway & School filters */}
<div className="grid grid-cols-2 gap-4">
  <div className="flex items-center gap-2 pt-5">
    <input
      type="checkbox"
      id="avoid_highways"
      checked={criteria.avoid_highways || false}
      onChange={(e) => setCriteria({ ...criteria, avoid_highways: e.target.checked })}
      className="rounded border-gray-300"
    />
    <label htmlFor="avoid_highways" className="text-xs font-medium text-gray-600">
      Avoid highways
    </label>
  </div>
  <div>
    <label className="block text-xs font-medium text-gray-600 mb-1">Min School Rating</label>
    <select
      value={criteria.school_rating_min || ''}
      onChange={setNum('school_rating_min')}
      className="w-full py-1.5 px-3 border rounded text-sm"
    >
      <option value="">Any</option>
      {[1,2,3,4,5,6,7,8,9,10].map(n => <option key={n} value={n}>{n}+</option>)}
    </select>
  </div>
</div>
```

Also ensure the initial criteria state in SearchForm includes `avoid_highways: false` and `school_rating_min: ''` (or null) so they are sent to the API.

**2b. PropertyCard.jsx -- add highway warning and school rating badges:**

After destructuring `listing`, extract the new fields:
```javascript
const { ..., near_highway, highway_name, school_rating, school_district } = listing
```

In the features array section (after `if (hoa_monthly)` line), add:
```javascript
if (school_rating) features.push(`School: ${school_rating}/10`)
```

After the features badges `<div>` (around line 91) and before the property type div, add a highway warning if applicable:
```jsx
{near_highway && (
  <div className="flex items-center gap-1 text-amber-600 text-xs font-medium mb-2">
    <span>&#9888;&#65039;</span> Near {highway_name || 'Highway'}
  </div>
)}
```

**2c. NewSearch.jsx -- replace flat grid with sectioned results:**

Replace the results rendering section (the block from line 97 `{results && !loading && (` through line 126 `)}`) with sectioned display logic.

Add a helper function inside the component (before the return statement):

```javascript
const groupResults = (listings) => {
  if (!listings || listings.length === 0) return []

  // Calculate max possible score (number of non-null criteria fields matched)
  // Simple heuristic: use the top listing's "quality" as reference
  const maxScore = listings.length

  const sections = [
    {
      key: 'perfect',
      icon: '\u2B50',
      title: 'Perfect Match',
      color: 'bg-yellow-50 border-yellow-300 text-yellow-800',
      headerColor: 'bg-yellow-100',
      filter: (l) => !l.near_highway && l.price && l.bedrooms && l.bathrooms && l.sqft,
      defaultOpen: true,
    },
    {
      key: 'strong',
      icon: '\u2705',
      title: 'Strong Match',
      color: 'bg-green-50 border-green-300 text-green-800',
      headerColor: 'bg-green-100',
      filter: (l) => !l.near_highway && l.price && (l.bedrooms || l.bathrooms),
      defaultOpen: false,
    },
    {
      key: 'good',
      icon: '\uD83C\uDFE0',
      title: 'Good Options',
      color: 'bg-blue-50 border-blue-300 text-blue-800',
      headerColor: 'bg-blue-100',
      filter: (l) => !l.near_highway,
      defaultOpen: false,
    },
    {
      key: 'highway',
      icon: '\u26A0\uFE0F',
      title: 'Near Highway',
      color: 'bg-amber-50 border-amber-300 text-amber-800',
      headerColor: 'bg-amber-100',
      filter: (l) => l.near_highway,
      defaultOpen: false,
    },
  ]

  // Assign each listing to the FIRST matching section (waterfall)
  const assigned = new Set()
  const grouped = sections.map(section => {
    const items = listings.filter(l => {
      if (assigned.has(l)) return false
      if (section.filter(l)) {
        assigned.add(l)
        return true
      }
      return false
    })
    return { ...section, items }
  }).filter(s => s.items.length > 0)

  return grouped
}
```

Add collapsed state:
```javascript
const [collapsedSections, setCollapsedSections] = useState({})
const toggleSection = (key) => setCollapsedSections(prev => ({ ...prev, [key]: !prev[key] }))
```

Replace the results grid with:
```jsx
{results && !loading && (
  <div className="mt-6">
    <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
      <h2 className="text-lg font-semibold text-slate-800">
        {results.total} Properties Found
        {results.search_name && <span className="text-brand-600 text-sm ml-2">(Saved as "{results.search_name}")</span>}
      </h2>
      <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
        className="py-1.5 px-3 border border-slate-200 rounded-lg text-sm">
        <option value="price_asc">Price: Low to High</option>
        <option value="price_desc">Price: High to Low</option>
        <option value="sqft_desc">Largest First</option>
        <option value="newest">Newest Built</option>
      </select>
    </div>

    {results.total === 0 ? (
      <p className="text-center text-slate-500 py-8">No properties match your criteria. Try adjusting your filters.</p>
    ) : (
      <div className="space-y-6">
        {groupResults(sortedResults()).map(section => {
          const isCollapsed = collapsedSections[section.key] ?? !section.defaultOpen
          return (
            <div key={section.key} className={`border rounded-lg overflow-hidden ${section.color}`}>
              <button
                onClick={() => toggleSection(section.key)}
                className={`w-full flex items-center justify-between px-4 py-3 ${section.headerColor} font-semibold text-sm`}
              >
                <span>{section.icon} {section.title} ({section.items.length})</span>
                <span className="text-xs">{isCollapsed ? '+ Show' : '- Hide'}</span>
              </button>
              {!isCollapsed && (
                <div className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {section.items.map((listing, i) => (
                      <PropertyCard key={`${listing.source}-${listing.source_id}-${i}`} listing={listing} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    )}
  </div>
)}
```
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr/frontend && npx vite build 2>&1 | tail -5</automated>
  </verify>
  <done>
    - SearchForm has "Avoid highways" checkbox and "Min School Rating" 1-10 select in advanced filters
    - PropertyCard shows highway warning badge and school rating in features
    - NewSearch groups results into collapsible sections: Perfect Match (open), Strong Match, Good Options, Near Highway (all collapsed by default)
    - Each section has colored header with icon, title, and count
    - Frontend builds without errors
  </done>
</task>

</tasks>

<verification>
1. Backend: `python -c "from homesearch.services.road_service import check_highway_proximity; from homesearch.services.school_service import get_school_rating; print('Services importable')"` succeeds
2. Models: New fields on SearchCriteria and Listing are accessible and defaulted correctly
3. Frontend: `cd frontend && npx vite build` completes without errors
4. Integration: Start server with `homesearch serve`, run a search with "Avoid highways" checked -- results should show sectioned view with highway-flagged listings in the last section
</verification>

<success_criteria>
- Two new service files exist and are importable
- SearchCriteria accepts avoid_highways and school_rating_min
- Listing carries near_highway, highway_name, school_rating, school_district
- run_search enriches listings conditionally (highway only when opted in)
- Frontend form has the two new controls in advanced filters
- Results display in collapsible sections grouped by match quality
- Highway-near listings appear in a dedicated warning section at bottom
- Frontend builds successfully
</success_criteria>

<output>
After completion, create `.planning/quick/260326-gam-highway-proximity-detection-school-ratin/260326-gam-SUMMARY.md`
</output>
