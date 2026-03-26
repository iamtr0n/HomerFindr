---
phase: quick
plan: 260326-gal
type: execute
wave: 1
depends_on: []
files_modified:
  - homesearch/models.py
  - homesearch/services/search_service.py
  - homesearch/tui/results.py
  - homesearch/tui/wizard.py
  - frontend/src/pages/NewSearch.jsx
  - frontend/src/components/PropertyCard.jsx
autonomous: true
must_haves:
  truths:
    - "Listings are scored by how many optional criteria they satisfy above minimums"
    - "Gold star listings (all criteria met) are visually distinguished in both CLI and web"
    - "Results are sorted by gold_star DESC, match_score DESC, price ASC"
    - "CLI shows score column with badges and supports paginated 50-at-a-time browsing"
    - "CLI loops back to listing selection after opening a URL in browser"
    - "CLI price wizard allows multi-select price ranges that combine into min/max"
    - "Web shows Best Match sort, gold star badges, match badge chips, and Load More pagination"
  artifacts:
    - path: "homesearch/services/search_service.py"
      provides: "_score_listing function, sorted results in run_search"
    - path: "homesearch/models.py"
      provides: "match_score and match_badges fields on Listing"
    - path: "homesearch/tui/results.py"
      provides: "Score column, badges, paginated display, back-nav loop"
    - path: "homesearch/tui/wizard.py"
      provides: "Multi-select price ranges with Custom option"
  key_links:
    - from: "homesearch/services/search_service.py"
      to: "homesearch/models.py"
      via: "Listing.match_score and Listing.match_badges populated by _score_listing"
    - from: "homesearch/tui/results.py"
      to: "homesearch/services/search_service.py"
      via: "display_results reads match_score/match_badges from scored+sorted listings"
---

<objective>
Add a scoring engine that rates listings by how many optional criteria they satisfy, attach match badges and gold star status, sort results by score, and upgrade both CLI and web interfaces to display scores with pagination and improved navigation.

Purpose: Help users instantly identify the best-matching properties and browse large result sets without hitting arbitrary caps.
Output: Scored/sorted listings with badges in both CLI table and web cards, paginated browsing, multi-select price in CLI wizard.
</objective>

<context>
@homesearch/models.py
@homesearch/services/search_service.py
@homesearch/tui/results.py
@homesearch/tui/wizard.py
@frontend/src/pages/NewSearch.jsx
@frontend/src/components/PropertyCard.jsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Scoring engine, model fields, sorted results, and CLI upgrades</name>
  <files>
    homesearch/models.py
    homesearch/services/search_service.py
    homesearch/tui/results.py
    homesearch/tui/wizard.py
  </files>
  <action>
**1. Model fields** (`homesearch/models.py`):
Add two fields to `Listing` after the existing fields (before `first_seen_at`):
```python
match_score: int = 0
match_badges: list[str] = Field(default_factory=list)
```

**2. Scoring engine** (`homesearch/services/search_service.py`):
Add `_score_listing(listing: Listing, criteria: SearchCriteria) -> tuple[int, list[str]]` after `_passes_filters`:
- Score counts how many *optional* (non-None) criteria the listing satisfies ABOVE minimum requirements
- Badge logic (add badge string when criterion is met):
  - `criteria.has_garage is True` and `listing.has_garage is True` -> "garage"
  - `criteria.has_basement is True` and `listing.has_basement is True` -> "basement"
  - `criteria.has_pool is True` and `listing.has_pool is True` -> "pool"
  - `criteria.has_fireplace is True` and `listing.has_fireplace is True` -> "fireplace"
  - `criteria.has_ac is True` and `listing.has_ac is True` -> "A/C"
  - `criteria.hoa_max is not None` and `listing.hoa_monthly is not None` and `listing.hoa_monthly <= criteria.hoa_max` -> "no HOA" if hoa_monthly == 0 else f"HOA ${listing.hoa_monthly:.0f}"
  - `criteria.bedrooms_min` and `listing.bedrooms` and `listing.bedrooms >= criteria.bedrooms_min` AND `criteria.bathrooms_min` and `listing.bathrooms` and `listing.bathrooms >= criteria.bathrooms_min` -> f"{listing.bedrooms}bd/{listing.bathrooms}ba {chr(10003)}"
  - `criteria.price_min is not None or criteria.price_max is not None`: if listing.price is within range -> "price {chr(10003)}"
  - `criteria.year_built_min` and `listing.year_built` and `listing.year_built >= criteria.year_built_min` -> "new build" (if year_built >= 2020, otherwise skip this badge)
  - `criteria.heat_type` and `criteria.heat_type != "any"` and `listing.heat_type == criteria.heat_type` -> listing.heat_type
- Score = len(badges)
- Compute `perfect_score` = count of non-None optional criteria fields in criteria (same fields checked above)
- Return (score, badges)

In `run_search()`, after the `filtered = [...]` line (line 91) and before the `if search_id` block:
```python
# Score and sort
perfect_score = _perfect_score(criteria)
for listing in filtered:
    score, badges = _score_listing(listing, criteria)
    listing.match_score = score
    listing.match_badges = badges

filtered.sort(key=lambda l: (
    -(1 if l.match_score >= perfect_score and perfect_score > 0 else 0),
    -l.match_score,
    l.price or float('inf'),
))
```
Add helper `_perfect_score(criteria)` that counts non-None optional criteria (same set as _score_listing checks).

**3. CLI results display** (`homesearch/tui/results.py`):
- In `display_results`, add a "Score" column after "Source" column:
  ```python
  table.add_column("Score", justify="center", width=10)
  ```
  For each row, compute: `perfect = max(l.match_score for l in results) if results else 0` (use the actual perfect from criteria if available, but match_score max works as display proxy). Show `f"{listing.match_score}/{max_score} {'star' if listing.match_score >= max_score and max_score > 0 else ''}"` — use the actual star emoji.
- Add a "Badges" column (width=20) showing `" . ".join(listing.match_badges)` (middle dot separator).
- **Pagination**: Replace `display = results[:50]` with a paginated loop:
  ```python
  page_size = 50
  offset = 0
  while offset < len(results):
      page = results[offset:offset + page_size]
      # build and print table for this page
      # ... (existing table logic but for `page` and numbering starts at offset+1)
      offset += page_size
      if offset < len(results):
          more = questionary.select(
              f"Showing {min(offset, len(results))} of {len(results)} — Show 50 more?",
              choices=["Yes", "No"],
              style=HOUSE_STYLE,
          ).ask()
          if not more or more == "No":
              break
  ```
- **Back navigation**: After opening a URL in `webbrowser.open()`, do NOT fall through to `_offer_save_search`. Instead, wrap the listing-selection prompt in a `while True` loop so after opening a URL it re-shows the select prompt. Only break out (to save-search prompt) when user picks "Back to menu".

**4. CLI multi-select price** (`homesearch/tui/wizard.py`):
Replace the price range `questionary.select` (section 6, lines 282-301) with `questionary.checkbox`:
```python
PRICE_RANGES = [
    "Under $200k",
    "$200k - $350k",
    "$350k - $500k",
    "$500k - $750k",
    "$750k - $1M",
    "Over $1M",
    "Custom range",
]

price_answers = questionary.checkbox(
    "Price range(s):",
    choices=PRICE_RANGES,
    style=HOUSE_STYLE,
    instruction="(Space to select, Enter to confirm)",
).ask()
if price_answers is None:
    return None
```
If "Custom range" is selected, prompt two `questionary.text` inputs for min and max (parse to int, allow empty for None).
Otherwise, map selected ranges to their min/max values:
- "Under $200k": (None, 200_000)
- "$200k - $350k": (200_000, 350_000)
- "$350k - $500k": (350_000, 500_000)
- "$500k - $750k": (500_000, 750_000)
- "$750k - $1M": (750_000, 1_000_000)
- "Over $1M": (1_000_000, None)
Combine multiple selections: price_min = lowest min (ignoring None), price_max = highest max (ignoring None). If no ranges selected, both are None.
Update `_parse_price_range` or add `_parse_multi_price` helper.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "
from homesearch.models import Listing, SearchCriteria
from homesearch.services.search_service import _score_listing
criteria = SearchCriteria(has_garage=True, has_basement=True, price_min=200000, price_max=500000)
listing = Listing(source='test', source_id='1', address='123 Main', price=300000, has_garage=True, has_basement=True)
score, badges = _score_listing(listing, criteria)
assert score >= 2, f'Expected score >= 2, got {score}'
assert 'garage' in badges, f'Missing garage badge: {badges}'
assert 'basement' in badges, f'Missing basement badge: {badges}'
print(f'OK: score={score}, badges={badges}')

# Verify model fields exist
assert hasattr(listing, 'match_score')
assert hasattr(listing, 'match_badges')
print('Model fields OK')
"
    </automated>
  </verify>
  <done>
    - `_score_listing` returns correct score and badge list for matching criteria
    - `run_search` returns listings sorted by gold_star DESC, match_score DESC, price ASC
    - Listing model has match_score and match_badges fields
    - CLI results table shows Score and Badges columns
    - CLI results paginate 50 at a time with "Show more?" prompt
    - CLI listing selection loops back after opening a URL (back navigation)
    - CLI wizard uses checkbox for multi-select price ranges with Custom option
  </done>
</task>

<task type="auto">
  <name>Task 2: Web frontend — Best Match sort, gold star, badges, Load More</name>
  <files>
    frontend/src/pages/NewSearch.jsx
    frontend/src/components/PropertyCard.jsx
  </files>
  <action>
**1. NewSearch.jsx — Sort and pagination:**
- Add `'best_match'` as the default `sortBy` state (change initial from `'price_asc'` to `'best_match'`).
- Add `best_match` case to `sortedResults()`:
  ```javascript
  case 'best_match': return list.sort((a, b) => {
    const aGold = (a.match_score || 0) >= perfectScore ? 1 : 0
    const bGold = (b.match_score || 0) >= perfectScore ? 1 : 0
    if (bGold !== aGold) return bGold - aGold
    if ((b.match_score || 0) !== (a.match_score || 0)) return (b.match_score || 0) - (a.match_score || 0)
    return (a.price || 0) - (b.price || 0)
  })
  ```
  Compute `perfectScore` as the max `match_score` across all results (or derive from criteria count — max is simpler).
- Add `<option value="best_match">Best Match</option>` as the first option in the sort `<select>`.
- **Load More pagination**: Add `const [visibleCount, setVisibleCount] = useState(50)` state.
  - In the grid rendering, slice: `sortedResults().slice(0, visibleCount)`.
  - After the grid div, add a "Load More" button:
    ```jsx
    {sortedResults().length > visibleCount && (
      <div className="text-center mt-6">
        <button
          onClick={() => setVisibleCount(v => v + 50)}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
        >
          Showing {visibleCount} of {results.total} — Load 50 more
        </button>
      </div>
    )}
    ```
  - Reset `visibleCount` to 50 when a new search is triggered (in `handleSearch`, add `setVisibleCount(50)`).
- **Back navigation**: The existing React state already preserves criteria when navigating back (SPA with useState). No explicit work needed — criteria state persists in the component. The browser back button behavior is already handled by React Router keeping the component mounted. If results are showing, add a "Back to Search" button above results that hides results and re-shows the form:
  ```jsx
  <button onClick={() => setResults(null)} className="text-sm text-blue-600 hover:text-blue-800 mb-4">
    &larr; Back to search
  </button>
  ```

**2. PropertyCard.jsx — Gold star and badges:**
- Destructure `match_score`, `match_badges` from `listing` (add to the existing destructure).
- Compute `isGoldStar`: check if `match_score` equals the max possible. Since we don't have perfect_score in the card, pass it as a prop or simply check if `listing.gold_star` is truthy. Simpler approach: compute in NewSearch.jsx and pass `isGoldStar` as a prop. In NewSearch.jsx, compute `const perfectScore = Math.max(...(results?.results || []).map(r => r.match_score || 0), 0)` and pass `isGoldStar={listing.match_score >= perfectScore && perfectScore > 0}` to PropertyCard.
- **Gold star card styling**: Add conditional border/ring to the Card:
  ```jsx
  <Card className={`overflow-hidden hover:shadow-md transition-shadow ${isGoldStar ? 'ring-2 ring-amber-400 border-amber-300' : ''}`}>
  ```
- **Gold star badge**: If `isGoldStar`, render a star badge near the source badge:
  ```jsx
  {isGoldStar && (
    <Badge className="absolute top-2 left-2 bg-amber-400 text-amber-900 shadow-sm">
      &#11088; Perfect Match
    </Badge>
  )}
  ```
- **Match badges as chips**: After the features section (or replacing it), render match_badges:
  ```jsx
  {match_badges && match_badges.length > 0 && (
    <div className="flex flex-wrap gap-1 mb-3">
      {match_badges.map((badge) => (
        <span key={badge} className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-700 border border-blue-200">
          {badge}
        </span>
      ))}
    </div>
  )}
  ```
  Keep the existing features badges too — match_badges go above them as a distinct row with blue styling (features keep outline variant).
- Accept `isGoldStar` prop: `export default function PropertyCard({ listing, isGoldStar = false })`
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr/frontend && npx vite build --mode production 2>&1 | tail -5</automated>
  </verify>
  <done>
    - "Best Match" is default sort option and sorts by gold_star DESC, match_score DESC, price ASC
    - Gold star listings have amber ring border and star badge on card
    - Match badges display as blue chips on each card
    - "Load 50 more" button appears when results exceed 50, loads next batch
    - "Back to search" button re-shows form with criteria preserved
    - Frontend builds without errors
  </done>
</task>

</tasks>

<verification>
- `python -c "from homesearch.services.search_service import _score_listing; print('import OK')"` succeeds
- `cd frontend && npx vite build` succeeds with no errors
- Listing model has match_score (int) and match_badges (list[str]) fields
</verification>

<success_criteria>
- Scoring engine correctly scores listings and attaches badges
- Results sorted by gold_star DESC, match_score DESC, price ASC in both CLI and web
- CLI table has Score and Badges columns, paginates 50 at a time, loops listing selection
- CLI wizard uses multi-select checkbox for price ranges
- Web has Best Match sort default, gold star visual treatment, badge chips, Load More button
</success_criteria>
