# Phase 5: Property Card Photos - Research

**Researched:** 2026-03-25
**Domain:** React JSX photo rendering, CDN referrer policy, homeharvest DataFrame photo columns, Redfin API photo key shapes
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Add `referrerPolicy="no-referrer"` to the `<img>` tag in `PropertyCard.jsx` — this suppresses the `Referer` header that triggers CDN hotlink blocking on rdcpix.com (Realtor.com's CDN)
- **D-02:** Diagnose FIRST before writing any code: (1) run a real search, check SQLite for non-null `photo_url` values, (2) open DevTools Network tab and confirm 403s on photo URLs, (3) then apply the fix and validate it resolves the 403s
- **D-03:** No server-side photo proxy — ToS risk, SSRF exposure with existing wildcard CORS policy, unnecessary complexity given the frontend fix is sufficient
- **D-04:** Add `alt_photos[0]` fallback in `homeharvest_provider.py` — if `primary_photo` is null/empty, use first element of `alt_photos` list as `photo_url`. One extra line in `_row_to_listing`. Do NOT do this for Redfin until the photo key instability is resolved.
- **D-05:** Diagnose Redfin photo key name with one-run logging (`print(raw_home.get("photos", {}).keys())`) before assuming current multi-shape handler covers it — this is a 30-second check, not optional
- **D-06:** Replace the plain "No Photo Available" text div with: `Home` icon (28-32px, `lucide-react`) centered + "No Photo Available" text label below it
- **D-07:** Background stays `bg-slate-100`, icon and text color `text-slate-400` — matches current card aesthetic, looks intentional not broken
- **D-08:** The placeholder div must remain `h-52` (same height as the photo) to preserve card height consistency across the results grid
- **D-09:** Keep existing `onError` behavior — hides `<img>` and shows placeholder div. Current approach is correct; just ensure it works after the `referrerPolicy` attribute is added (should be transparent)
- **D-10:** Add `animate-pulse` to the placeholder div while image is potentially loading — signals something is coming. Implementation: placeholder shows with pulse animation by default; when `onLoad` fires, cancel the animation (or use CSS `[img loaded]` state). Keep it subtle — single pulse class, no custom keyframes.

### Claude's Discretion
- Exact Tailwind classes for `animate-pulse` integration (use standard Tailwind pulse, not custom keyframes)
- Whether to use `onLoad` to stop the pulse or just leave pulse running always for the placeholder
- Icon import placement in PropertyCard.jsx (add `Home` to existing lucide-react import line)

### Deferred Ideas (OUT OF SCOPE)
- Alt photos gallery/carousel — significant React complexity, deferred to v2+
- Server-side photo proxy — explicitly rejected (ToS, SSRF, complexity)
- Redfin `alt_photos` fallback — defer until Redfin photo key instability is diagnosed and confirmed fixed in Phase 5
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PHOTO-01 | User can see real listing thumbnail photos in property cards on the web dashboard | D-01 (referrerPolicy fix), D-02 (diagnose-first protocol), D-04 (alt_photos fallback), D-05 (Redfin diagnostic) |
| PHOTO-02 | Property cards display a polished placeholder when no listing photo is available | D-06 (Home icon), D-07 (colors), D-08 (h-52 height), D-09 (onError), D-10 (animate-pulse) |
</phase_requirements>

---

## Summary

Phase 5 is a focused repair-and-polish phase. The root cause of photos not displaying in the web dashboard is almost certainly a CDN hotlink blocking issue: Realtor.com's CDN (rdcpix.com) rejects requests that include a `Referer` header pointing to localhost. The fix is a single attribute addition — `referrerPolicy="no-referrer"` on the `<img>` element in `PropertyCard.jsx`. This is a standard W3C Referrer Policy browser mechanism and is the minimal correct solution.

Two supporting changes accompany the CDN fix: (1) adding an `alt_photos[0]` fallback in the homeharvest provider for listings where `primary_photo` is null, and (2) upgrading the placeholder div from bare text to a styled `Home` icon + label. Both are small and self-contained. A third concern — Redfin photo key instability — requires a diagnose-first step before any provider code is touched.

The UI-SPEC.md has already resolved all discretionary decisions (animate-pulse approach, state management mechanism, exact class strings, onError/onLoad wiring). The planner's job is to sequence tasks in the correct diagnose-before-code order and give executors the exact line numbers and strings they need to make changes without ambiguity.

**Primary recommendation:** Follow the diagnose-first protocol exactly (D-02, D-05) — confirm `photo_url` is populated in SQLite and confirm the 403 in DevTools before writing a single line of code. Once confirmed, the implementation is three discrete edits across two files.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | ^18.3.1 (installed) | Component state, JSX rendering | Existing project framework |
| lucide-react | ^0.424.0 (installed) | `Home` icon for placeholder | Already in `package.json`; no new install |
| Tailwind CSS | ^3.4.7 (installed) | `animate-pulse`, `bg-slate-100`, `h-52` utility classes | Existing project CSS system |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| homeharvest | >=0.4.0 (installed) | Source of `primary_photo` + `alt_photos` columns | Provider-side fallback only |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `referrerPolicy="no-referrer"` | Server-side proxy | Proxy rejected (D-03): ToS risk, SSRF exposure, zero added value |
| `useState` for pulse control | CSS-only `:has(img)` pseudo-selector | CSS approach has cross-browser gaps and requires data-attribute toggle anyway — same cost, less readable |

**Installation:** No new packages. Zero new `npm install` or `pip install` commands.

---

## Architecture Patterns

### Recommended Project Structure

No structural changes. All edits confined to two existing files:

```
frontend/src/components/PropertyCard.jsx   — JSX changes (img + placeholder)
homesearch/providers/homeharvest_provider.py — Python one-liner (alt_photos fallback)
```

### Pattern 1: CDN Referrer Suppression via `referrerPolicy`

**What:** Adding `referrerPolicy="no-referrer"` to an `<img>` element instructs the browser to omit the `Referer` HTTP header when fetching the image. CDNs that use allowlist-based hotlink protection check this header; when it is absent, the CDN typically allows the request.

**When to use:** Any time browser-rendered images from a third-party CDN return 403 Forbidden and the CDN uses `Referer`-based hotlink protection. This is the standard browser mechanism (W3C Referrer Policy Level 1).

**Example:**
```jsx
// Source: W3C Referrer Policy / MDN — standard browser attribute
<img
  src={photo_url}
  alt={address}
  className="w-full h-52 object-cover bg-slate-100"
  referrerPolicy="no-referrer"
  onLoad={() => setImgLoaded(true)}
  onError={(e) => {
    e.target.style.display = 'none'
    e.target.nextSibling.style.display = 'flex'
    setImgLoaded(true)
  }}
/>
```

### Pattern 2: Conditional `animate-pulse` via `useState`

**What:** A single `useState(false)` boolean (`imgLoaded`) tracks whether the image has resolved. The placeholder div uses a computed class string that includes `animate-pulse` only when `photo_url` is truthy AND `imgLoaded` is false. Both `onLoad` and `onError` set `imgLoaded = true`, ensuring the pulse stops in all terminal states.

**When to use:** Any time a skeleton/pulse loading indicator needs to stop on image resolution without custom CSS keyframes.

**Example (from 05-UI-SPEC.md):**
```jsx
// Source: 05-UI-SPEC.md — resolved discretionary decision
const [imgLoaded, setImgLoaded] = useState(false)

const placeholderClass = `w-full h-52 bg-slate-100 flex flex-col items-center justify-center text-slate-400 gap-2${photo_url && !imgLoaded ? ' animate-pulse' : ''}`
```

**State table:**

| Condition | `imgLoaded` | Placeholder visible | `animate-pulse` |
|-----------|-------------|---------------------|-----------------|
| No `photo_url` | unused | yes (flex, default) | no |
| `photo_url`, loading | false | yes | yes |
| `onLoad` fired | true | no (display:none) | no |
| `onError` fired | true | yes (restored by handler) | no |

### Pattern 3: homeharvest `alt_photos` Fallback

**What:** After extracting `primary_photo`, check if the result is falsy and if so use the first element of `alt_photos`. Both values are available as columns in the homeharvest DataFrame.

**Column format confirmed (installed source `utils.py` line 137):**
- `primary_photo`: `str | None` — `str(description.primary_photo)` (already stringified from `HttpUrl`)
- `alt_photos`: `str | None` — comma-joined string: `", ".join(str(url) for url in description.alt_photos)` — NOT a list

This is critical: `alt_photos` in the DataFrame is a **comma-delimited string**, not a Python list. Splitting on `", "` gives the individual URLs.

**Example:**
```python
# In _row_to_listing(), replacing the current single-line photo extraction:
# CURRENT (line 107):
photo = str(row.get("primary_photo", "") or row.get("img_src", "") or "")

# REPLACEMENT (adds alt_photos fallback):
photo = str(row.get("primary_photo", "") or row.get("img_src", "") or "")
if not photo:
    alt = str(row.get("alt_photos", "") or "")
    if alt:
        photo = alt.split(", ")[0]
```

### Anti-Patterns to Avoid

- **Touching `redfin_provider.py` before running diagnostic logging:** The existing `_home_to_listing` already has multi-shape photo handling. The key name may or may not be current. Run the diagnostic first (`print(home_data.get("photos", "NO_KEY"))`) before assuming it needs changes.
- **Adding `alt_photos` to the `Listing` model:** The model already has `photo_url: str = ""`. The alt fallback should be resolved in the provider (pick best URL, assign to `photo_url`) — not by adding a new field that propagates to the API and frontend.
- **Changing the DOM order of `<img>` and placeholder div:** The `onError` handler uses `e.target.nextSibling` to locate the placeholder. If any element is inserted between them, the handler silently fails — the placeholder never appears.
- **Passing `setImgLoaded` to `onError` without also hiding the `<img>`:** The `onError` handler must keep both DOM manipulation (`style.display = 'none'`) and state update (`setImgLoaded(true)`) to correctly hide the broken image AND remove the pulse from the placeholder.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CDN hotlink bypass | Server-side proxy endpoint | `referrerPolicy="no-referrer"` HTML attribute | Proxy adds ToS risk, SSRF exposure, FastAPI route, wildcard CORS issue; attribute is one word |
| Loading skeleton animation | Custom CSS `@keyframes` | Tailwind `animate-pulse` | Already in Tailwind config; consistent with existing Tailwind-only styling |
| Photo URL resolution | New `Listing` model field + API change | Provider-side fallback in `_row_to_listing()` | Keeps model stable; no API contract change; one-line fix |

**Key insight:** Every problem in this phase has a solution that is already available in the installed stack. The correct solutions are all smaller than any custom alternative.

---

## Current Code State (Exact)

### PropertyCard.jsx — Current Photo Block

**File:** `frontend/src/components/PropertyCard.jsx`

**Line 1 — Imports:**
```jsx
import { ExternalLink, Bed, Bath, Ruler, Calendar } from 'lucide-react'
```
`Home` is NOT yet imported. `useState` is NOT yet imported from React (React itself is not imported — function component uses no hooks currently).

**Lines 27-42 — Photo block:**
```jsx
<a href={source_url || '#'} target="_blank" rel="noopener noreferrer" className="relative block">
  {photo_url ? (
    <img
      src={photo_url}
      alt={address}
      className="w-full h-52 object-cover bg-slate-100"
      onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
    />
  ) : null}
  <div className={`w-full h-52 bg-slate-100 items-center justify-center text-slate-400 text-sm ${photo_url ? 'hidden' : 'flex'}`}>
    No Photo Available
  </div>
  <Badge variant="secondary" className="absolute top-2 right-2 capitalize shadow-sm">
    {source}
  </Badge>
</a>
```

**Key observations:**
- No `referrerPolicy` — this is the bug
- No `onLoad` handler
- No `useState` / no `imgLoaded` state
- `React` is not imported (component uses no hooks currently — `useState` import requires adding `import { useState } from 'react'` as a new line)
- Placeholder uses `'hidden'` class when `photo_url` is truthy; the `onError` handler overrides this with `style.display = 'flex'` via DOM mutation — this is intentional but fragile
- Placeholder content is bare text `No Photo Available` — no icon
- Placeholder uses `text-sm` (14px); spec calls for `text-xs` (12px) for the label
- `<img>` and placeholder div ARE adjacent siblings — `nextSibling` is correct for the current DOM order

### homeharvest_provider.py — Current Photo Extraction

**File:** `homesearch/providers/homeharvest_provider.py`

**Line 107 (inside `_row_to_listing`):**
```python
photo = str(row.get("primary_photo", "") or row.get("img_src", "") or "")
```

**What this does:**
- Tries `primary_photo` first (confirmed column name in `utils.py:ordered_properties`)
- Falls back to `img_src` (legacy column name from earlier homeharvest versions — defensive)
- No `alt_photos` fallback currently
- Photo is passed to `Listing(photo_url=photo, ...)` at line 161

**`alt_photos` column format (confirmed from installed source `utils.py` line 137):**
```python
prop_data["alt_photos"] = ", ".join(str(url) for url in description.alt_photos) if description.alt_photos else None
```
Result: comma-separated string of URLs (e.g. `"https://a.com/1.jpg, https://b.com/2.jpg"`), or `None`. Splitting on `", "` gives individual URLs.

**Fallback insertion point:** After line 107, before line 109 (the `desc` comment).

### redfin_provider.py — Current Photo Extraction

**File:** `homesearch/providers/redfin_provider.py`

**Lines 112-117 (inside `_home_to_listing`):**
```python
photo_url = ""
photos = home_data.get("photos", home_data.get("staticMapUrl"))
if isinstance(photos, list) and photos:
    photo_url = photos[0].get("photoUrl", "") if isinstance(photos[0], dict) else str(photos[0])
elif isinstance(photos, str):
    photo_url = photos
```

**Multi-shape handler breakdown:**
- Tries `home_data["photos"]` first; falls back to `home_data["staticMapUrl"]` as the key
- If result is a list: assumes items are dicts with `"photoUrl"` key, or bare strings
- If result is a string: uses it directly (captures the `staticMapUrl` fallback case)
- Does NOT try `"url"`, `"href"`, `"imageUrl"`, or other known variant key names

**Instability risk:** The `"photoUrl"` key name inside photo dicts is undocumented. The multi-shape code itself is evidence this was previously broken and patched. The diagnostic logging step must confirm whether the current live API returns `"photoUrl"` or something else.

**Diagnostic command to add temporarily (per D-05):**
```python
# Add at the top of _home_to_listing(), just after home_data extraction:
print(f"[Redfin DEBUG photos] type={type(home_data.get('photos'))}, keys={list(home_data.get('photos', [{}])[0].keys()) if isinstance(home_data.get('photos'), list) and home_data.get('photos') else 'n/a'}")
```

---

## Common Pitfalls

### Pitfall 1: `onError` nextSibling DOM order sensitivity

**What goes wrong:** If any JSX element is inserted between `<img>` and the placeholder `<div>`, `e.target.nextSibling` points to the wrong element. The placeholder stays hidden after image error; no visual fallback appears.

**Why it happens:** The `onError` handler uses raw DOM traversal (`nextSibling`) rather than a React ref or state. It is fragile by design — a deliberate tradeoff for simplicity.

**How to avoid:** Keep `<img>` and placeholder `<div>` as immediately adjacent siblings. No comments, no fragments, no conditional elements between them. The Badge is AFTER the placeholder div (currently at line 39) — that is fine.

**Warning signs:** Photo error produces a broken image icon instead of the styled placeholder.

### Pitfall 2: `hidden` class vs inline style conflict

**What goes wrong:** The current placeholder uses Tailwind `hidden` class (which sets `display: none` via CSS). The `onError` handler sets `style.display = 'flex'` via inline style. Inline styles take precedence over class-based styles in browsers, so this works. However, if `imgLoaded` state management adds another toggle mechanism, two systems compete for `display` control.

**Why it happens:** The code mixes class-based and inline-style-based visibility toggling.

**How to avoid:** The UI-SPEC.md pattern resolves this cleanly: when `photo_url` is truthy, render the `<img>` (visible by default, no hidden class), render placeholder visible by default, and use `onLoad` to set `style={{ display: 'none' }}` on the placeholder via `imgLoaded` state. The `onError` handler restores `style.display = 'flex'` on the placeholder (same as current). This removes the `hidden` class entirely from the placeholder — only inline style controls visibility when `photo_url` is present.

**Warning signs:** Placeholder shows briefly then disappears even when image loads successfully (or vice versa).

### Pitfall 3: `useState` requires React import

**What goes wrong:** `PropertyCard.jsx` currently has NO React import line. All existing hooks (`Bed`, `Bath`, etc.) are lucide-react, not React. Adding `useState` without adding the React import causes a runtime error: `useState is not defined`.

**Why it happens:** Modern React with Vite JSX transform does not require `import React from 'react'` for JSX, but named hooks like `useState` still require explicit import.

**How to avoid:** Add `import { useState } from 'react'` as the first line of `PropertyCard.jsx`.

**Warning signs:** `ReferenceError: useState is not defined` in browser console on component mount.

### Pitfall 4: `alt_photos` DataFrame column is a comma-joined string, not a list

**What goes wrong:** Developer assumes `row.get("alt_photos")` returns a Python list of URL strings and writes `row.get("alt_photos")[0]`. This raises `TypeError` because the value is a string (or `None`).

**Why it happens:** homeharvest's `process_result()` serializes the list into a comma-joined string for DataFrame compatibility (`", ".join(str(url) for url in description.alt_photos)`). The string representation is correct; indexing it as a list is not.

**How to avoid:** Split on `", "` before indexing: `alt.split(", ")[0]`. Wrap in a null check.

**Warning signs:** `TypeError` in `_row_to_listing()` traceback during homeharvest scrape.

### Pitfall 5: `primary_photo` column may be absent in some DataFrame builds

**What goes wrong:** If a future homeharvest version renames or removes the `primary_photo` column, `row.get("primary_photo")` silently returns `None` for all rows — no photos, no error. The `img_src` fallback at line 107 is already evidence of a previous rename.

**Why it happens:** homeharvest wraps an unofficial API; schema changes without versioning.

**How to avoid:** Run `print([c for c in df.columns if "photo" in c.lower()])` during the Phase 5 diagnosis step (D-02). Confirm `primary_photo` and `alt_photos` appear. If a different name appears (e.g., `img_src` again), update the extraction accordingly.

**Warning signs:** Zero `photo_url` values in SQLite after a successful search run.

### Pitfall 6: animate-pulse on placeholder when `photo_url` is falsy (no-photo state)

**What goes wrong:** If `animate-pulse` is added unconditionally (not gated on `photo_url && !imgLoaded`), the placeholder pulses forever even for listings that genuinely have no photo. This looks broken — it implies something is loading when nothing will ever arrive.

**Why it happens:** Naive implementation adds `animate-pulse` to the placeholder's static class string.

**How to avoid:** Gate the class on `photo_url && !imgLoaded` as specified in 05-UI-SPEC.md. When there is no photo URL at all, the placeholder renders without pulse (final state, nothing pending).

**Warning signs:** All "No Photo Available" placeholders in the results grid are pulsing continuously.

---

## Code Examples

Verified patterns from code inspection and 05-UI-SPEC.md:

### Complete updated PropertyCard photo block (from 05-UI-SPEC.md)

```jsx
// Add at top of file:
import { useState } from 'react'
import { ExternalLink, Bed, Bath, Ruler, Calendar, Home } from 'lucide-react'

// Inside component function body:
const [imgLoaded, setImgLoaded] = useState(false)

const placeholderClass = `w-full h-52 bg-slate-100 flex flex-col items-center justify-center text-slate-400 gap-2${photo_url && !imgLoaded ? ' animate-pulse' : ''}`

// JSX photo block:
<a href={source_url || '#'} target="_blank" rel="noopener noreferrer" className="relative block">
  {photo_url ? (
    <img
      src={photo_url}
      alt={address}
      className="w-full h-52 object-cover bg-slate-100"
      referrerPolicy="no-referrer"
      onLoad={() => setImgLoaded(true)}
      onError={(e) => {
        e.target.style.display = 'none'
        e.target.nextSibling.style.display = 'flex'
        setImgLoaded(true)
      }}
    />
  ) : null}
  <div
    className={placeholderClass}
    style={photo_url && imgLoaded ? { display: 'none' } : undefined}
  >
    <Home size={28} />
    <span className="text-xs">No Photo Available</span>
  </div>
  <Badge variant="secondary" className="absolute top-2 right-2 capitalize shadow-sm">
    {source}
  </Badge>
</a>
```

### alt_photos fallback in `_row_to_listing()` (homeharvest_provider.py)

```python
# Replace line 107 with:
photo = str(row.get("primary_photo", "") or row.get("img_src", "") or "")
if not photo:
    alt = str(row.get("alt_photos", "") or "")
    if alt:
        photo = alt.split(", ")[0]
```

### Redfin diagnostic logging (temporary, for D-05)

```python
# Add immediately after line 87 in redfin_provider.py (after home_data = home.get("homeData", home)):
photos_raw = home_data.get("photos")
print(f"[Redfin DEBUG] photos type={type(photos_raw).__name__}, "
      f"first_keys={list(photos_raw[0].keys()) if isinstance(photos_raw, list) and photos_raw and isinstance(photos_raw[0], dict) else repr(photos_raw)[:80]}")
```

### df.columns diagnostic command (D-02)

```python
# Add temporarily after df is returned in homeharvest_provider.py search():
print("[HH DEBUG] photo columns:", [c for c in df.columns if "photo" in c.lower()])
print("[HH DEBUG] sample primary_photo:", df["primary_photo"].dropna().head(3).tolist() if "primary_photo" in df.columns else "COLUMN MISSING")
```

### SQLite photo_url check (D-02 step)

```bash
sqlite3 ~/.homesearch/homesearch.db "SELECT photo_url FROM listings WHERE photo_url != '' LIMIT 5;"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `img_src` column name | `primary_photo` column name | Prior homeharvest version | `img_src` fallback still in code at line 107 as defensive measure |
| Bare text placeholder | Home icon + label | Phase 5 (this phase) | Placeholder looks intentional, not broken |
| No referrerPolicy | `referrerPolicy="no-referrer"` | Phase 5 (this phase) | Resolves CDN 403 for rdcpix.com images |

---

## Open Questions

1. **Is `photo_url` actually populated in SQLite after a real search?**
   - What we know: `_row_to_listing()` line 107 extracts `primary_photo` from the DataFrame; `primary_photo` is confirmed in `ordered_properties`
   - What's unclear: Coverage rate — what percentage of active listings have `primary_photo` populated vs. null
   - Recommendation: Run diagnosis step D-02 (SQLite check) before assuming CDN is the only issue; if coverage is near-zero, the alt_photos fallback becomes higher priority

2. **Does Redfin's current live API return `"photoUrl"` inside photo dict items?**
   - What we know: The existing `_home_to_listing` handles three shapes; `"photoUrl"` is what the code currently expects for dict items
   - What's unclear: Whether the live API still uses `"photoUrl"` or has shifted to another key
   - Recommendation: Run diagnostic logging (D-05) on one real Redfin search; read the output before touching any provider code

3. **Does `referrerPolicy="no-referrer"` resolve the Redfin CDN as well?**
   - What we know: The fix is confirmed correct for Realtor.com (rdcpix.com); Redfin uses a different CDN
   - What's unclear: Whether Redfin photo CDN also requires referrer suppression or is open
   - Recommendation: After applying the fix, check Network tab for both realtor-sourced and redfin-sourced photo requests

---

## Sources

### Primary (HIGH confidence)
- `/Users/iamtron/Documents/GitHub/HomerFindr/frontend/src/components/PropertyCard.jsx` — exact current code, line numbers, class strings, onError handler, import list
- `/Users/iamtron/Documents/GitHub/HomerFindr/homesearch/providers/homeharvest_provider.py` — exact current photo extraction (line 107), `_row_to_listing()` structure
- `/Users/iamtron/Documents/GitHub/HomerFindr/homesearch/providers/redfin_provider.py` — exact current multi-shape photo handler (lines 112-117)
- `/Users/iamtron/Documents/GitHub/HomerFindr/.venv/lib/python3.11/site-packages/homeharvest/utils.py` — `ordered_properties` list (confirms `primary_photo` and `alt_photos` column names); `process_result()` (confirms `alt_photos` is comma-joined string, not a list)
- `/Users/iamtron/Documents/GitHub/HomerFindr/.venv/lib/python3.11/site-packages/homeharvest/core/scrapers/models.py` — `Description.primary_photo: HttpUrl | None`, `Description.alt_photos: list[HttpUrl] | None` (source type before DataFrame serialization)
- `/Users/iamtron/Documents/GitHub/HomerFindr/.planning/phases/05-property-card-photos/05-CONTEXT.md` — all locked decisions, discretionary areas, deferred scope
- `/Users/iamtron/Documents/GitHub/HomerFindr/.planning/phases/05-property-card-photos/05-UI-SPEC.md` — complete placeholder spec, state machine, exact class strings, onLoad/onError wiring

### Secondary (MEDIUM confidence)
- `/Users/iamtron/Documents/GitHub/HomerFindr/.planning/research/SUMMARY.md` — CDN hotlink mechanism, Redfin key instability, homeharvest column drift (all confirmed by codebase inspection)
- W3C Referrer Policy Level 1 — `referrerPolicy="no-referrer"` suppresses `Referer` header on image fetch (standard browser behavior; no official Realtor.com CDN documentation available)

### Tertiary (LOW confidence)
- None for this phase.

---

## Metadata

**Confidence breakdown:**
- Current code state: HIGH — read directly from source files, exact line numbers cited
- Standard stack: HIGH — all libraries already installed, no new dependencies
- Architecture patterns: HIGH — all patterns derived from installed package source and existing codebase conventions
- Pitfalls: HIGH — all derived from direct code inspection (DOM nextSibling pattern, hidden class vs inline style, missing React import, alt_photos string format)
- alt_photos column format: HIGH — confirmed from installed `utils.py` process_result() source
- Redfin photo key: MEDIUM — instability flagged; diagnostic required before confident claim

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (homeharvest is actively maintained; column names could drift with minor version bumps — re-verify before executing if more than a few days pass)
