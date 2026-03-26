---
phase: quick
plan: 260326-erx
type: execute
wave: 1
depends_on: []
files_modified:
  - homesearch/services/zip_service.py
  - homesearch/api/routes.py
  - frontend/src/api.js
  - frontend/src/components/SearchForm.jsx
autonomous: true
must_haves:
  truths:
    - "Typing 'Rockville Center NY' returns Rockville Centre, NY (not Maryland)"
    - "Location input shows typeahead suggestions after 3+ chars with 300ms debounce"
    - "Selecting a suggestion sets the location field and closes the dropdown"
    - "State abbreviation or name in query filters results to that state"
  artifacts:
    - path: "homesearch/services/zip_service.py"
      provides: "State-aware filtering in discover_zip_codes + _parse helpers"
    - path: "homesearch/api/routes.py"
      provides: "GET /api/locations/search endpoint"
    - path: "frontend/src/api.js"
      provides: "searchLocations API method"
    - path: "frontend/src/components/SearchForm.jsx"
      provides: "Typeahead dropdown on location input"
  key_links:
    - from: "frontend/src/components/SearchForm.jsx"
      to: "/api/locations/search"
      via: "api.searchLocations called on debounced input"
      pattern: "api\\.searchLocations"
    - from: "homesearch/api/routes.py"
      to: "uszipcode.SearchEngine"
      via: "by_city search with state filtering"
      pattern: "search\\.by_city"
---

<objective>
Fix state-aware location disambiguation so "Rockville Center NY" resolves to New York (not Maryland), and add typeahead autocomplete to the web frontend location input.

Purpose: Users typing a city + state get filtered results for the correct state, and can pick from disambiguated suggestions when multiple cities match.
Output: Backend location search endpoint, fixed zip_service state filtering, frontend typeahead dropdown.
</objective>

<context>
@homesearch/services/zip_service.py
@homesearch/api/routes.py
@frontend/src/api.js
@frontend/src/components/SearchForm.jsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — location search endpoint + state-aware zip filtering</name>
  <files>homesearch/api/routes.py, homesearch/services/zip_service.py</files>
  <action>
1. In `zip_service.py`, fix `discover_zip_codes` so that when `_parse_state` returns a non-empty state string, the `by_city` fallback (line 35) also filters by state. Currently line 28-33 calls `by_city_and_state` but if it returns nothing, line 35 falls back to `by_city` alone — losing the state filter. Fix: after the `by_city` fallback on line 35, if `_parse_state(location_clean)` returned a value, filter results to only those matching that state abbreviation before taking the first result. Also filter the `by_city_and_state` results similarly (uszipcode sometimes returns cross-state results).

2. In `routes.py`, add a new endpoint BEFORE the static file mount (before line 223):

```python
@app.get("/api/locations/search")
def search_locations(q: str = ""):
    """Typeahead location search — returns unique city+state pairs."""
    from uszipcode import SearchEngine
    q = q.strip()
    if len(q) < 2:
        return {"suggestions": []}

    search = SearchEngine()

    # Parse state from query if present (reuse zip_service helpers)
    from homesearch.services.zip_service import _parse_city, _parse_state
    city_part = _parse_city(q)
    state_part = _parse_state(q)

    # Search by city name — uszipcode returns zip records, we extract unique city+state
    results = search.by_city(city=city_part, returns=50)

    # Filter to specified state if user typed one
    if state_part:
        results = [r for r in results if (r.state or "").upper() == state_part.upper()
                   or (r.state_abbr if hasattr(r, 'state_abbr') else r.state or "").upper() == state_part.upper()]

    # Build unique city+state suggestions
    seen = set()
    suggestions = []
    for r in results:
        city = r.major_city or r.post_office_city or ""
        state = r.state or ""
        key = f"{city.upper()}|{state.upper()}"
        if key not in seen and city:
            seen.add(key)
            suggestions.append({"city": city, "state": state})
        if len(suggestions) >= 8:
            break

    return {"suggestions": suggestions}
```

Note: uszipcode `Zipcode` objects have `.state` (abbreviation like "NY") — check at runtime. The filter should compare against both `r.state` (which is the abbreviation) to be safe.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "
from homesearch.services.zip_service import discover_zip_codes, _parse_city, _parse_state
# Test state parsing
assert _parse_state('Rockville Center NY') == 'NY', 'State parse failed'
assert _parse_city('Rockville Center NY') == 'Rockville Center', 'City parse failed'
# Test that discover returns NY not MD
results = discover_zip_codes('Rockville Center NY', radius_miles=5)
if results:
    assert any(z.state == 'NY' for z in results[:5]), f'Expected NY in top results, got: {[(z.city, z.state) for z in results[:5]]}'
print('OK: state-aware filtering works')
" && python -c "
from homesearch.api.routes import app
from fastapi.testclient import TestClient
client = TestClient(app)
resp = client.get('/api/locations/search?q=Rockville NY')
data = resp.json()
assert resp.status_code == 200
assert len(data['suggestions']) > 0
states = [s['state'] for s in data['suggestions']]
assert all(s in ('NY', 'New York') for s in states), f'Expected only NY, got {states}'
print('OK: location search endpoint filters by state')
"</automated>
  </verify>
  <done>
    - GET /api/locations/search?q=Rockville+NY returns only NY suggestions
    - discover_zip_codes("Rockville Center NY") returns NY zip codes, not MD
    - _parse_state and _parse_city correctly split city+state strings
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — typeahead autocomplete on location input</name>
  <files>frontend/src/api.js, frontend/src/components/SearchForm.jsx</files>
  <action>
1. In `api.js`, add to the `api` object (after `discoverZips`):

```javascript
// Location autocomplete
searchLocations: (query) =>
  request(`/locations/search?q=${encodeURIComponent(query)}`),
```

2. In `SearchForm.jsx`:

- Add `useEffect, useRef` to the React import
- Add state: `const [suggestions, setSuggestions] = useState([])` and `const [showSuggestions, setShowSuggestions] = useState(false)`
- Add a ref: `const debounceRef = useRef(null)` and `const wrapperRef = useRef(null)`
- Replace the `onChange={set('location')}` on the location input with a handler that:
  a. Updates `criteria.location` with the typed value
  b. Clears any existing debounce timer via `clearTimeout(debounceRef.current)`
  c. If value.length >= 3, sets a new 300ms timeout that calls `api.searchLocations(value)` and sets `suggestions` + `showSuggestions(true)`
  d. If value.length < 3, sets `suggestions([])` and `showSuggestions(false)`
- Add `onFocus` to re-show suggestions if they exist
- Add a click-outside handler via `useEffect` that listens for mousedown outside `wrapperRef` and closes suggestions
- Add onKeyDown handler: Escape closes dropdown
- Render the dropdown directly below the input (inside the `relative flex-1` div that wraps the input):

```jsx
{showSuggestions && suggestions.length > 0 && (
  <ul className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
    {suggestions.map((s, i) => (
      <li
        key={`${s.city}-${s.state}-${i}`}
        onMouseDown={(e) => {
          e.preventDefault()
          setCriteria({ ...criteria, location: `${s.city}, ${s.state}` })
          setShowSuggestions(false)
          setSuggestions([])
        }}
        className="px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 flex items-center gap-2"
      >
        <MapPin size={14} className="text-gray-400 shrink-0" />
        <span>{s.city}, <span className="text-gray-500">{s.state}</span></span>
      </li>
    ))}
  </ul>
)}
```

Use `onMouseDown` with `e.preventDefault()` (not onClick) so the selection fires before the input's `onBlur` closes the dropdown.

Wrap the existing `<div className="relative flex-1">` with `ref={wrapperRef}` for the click-outside detection.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr/frontend && npx vite build 2>&1 | tail -5</automated>
  </verify>
  <done>
    - Location input shows typeahead dropdown after typing 3+ characters
    - Suggestions display as "City, State" with MapPin icon
    - Selecting a suggestion sets location field and closes dropdown
    - Escape key and clicking outside close the dropdown
    - Frontend builds without errors
  </done>
</task>

</tasks>

<verification>
1. Backend: `python -c "from homesearch.services.zip_service import discover_zip_codes; r = discover_zip_codes('Rockville Center NY', 5); print([(z.city, z.state) for z in r[:3]])"` — should show NY results
2. Backend: `curl 'http://127.0.0.1:8000/api/locations/search?q=Rockville+NY'` — should return only NY suggestions
3. Frontend: Build succeeds, location input has typeahead behavior
</verification>

<success_criteria>
- "Rockville Center NY" resolves to New York zip codes, not Maryland
- Location typeahead shows disambiguated city+state suggestions
- State abbreviation in query string filters results to that state
- Frontend builds cleanly
</success_criteria>
