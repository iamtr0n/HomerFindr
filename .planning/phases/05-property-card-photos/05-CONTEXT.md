# Phase 5: Property Card Photos - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Diagnose why listing photos aren't rendering in the web dashboard, fix the root cause (CDN hotlink blocking via referrerPolicy), add alt_photos[0] fallback in the homeharvest provider, and polish the no-photo placeholder. No backend proxy. No photo gallery or carousel. Redfin photo key instability must be diagnosed with logging before touching any provider code.

</domain>

<decisions>
## Implementation Decisions

### Photo fix approach
- **D-01:** Add `referrerPolicy="no-referrer"` to the `<img>` tag in `PropertyCard.jsx` — this suppresses the `Referer` header that triggers CDN hotlink blocking on rdcpix.com (Realtor.com's CDN)
- **D-02:** Diagnose FIRST before writing any code: (1) run a real search, check SQLite for non-null `photo_url` values, (2) open DevTools Network tab and confirm 403s on photo URLs, (3) then apply the fix and validate it resolves the 403s
- **D-03:** No server-side photo proxy — ToS risk, SSRF exposure with existing wildcard CORS policy, unnecessary complexity given the frontend fix is sufficient

### alt_photos fallback
- **D-04:** Add `alt_photos[0]` fallback in `homeharvest_provider.py` — if `primary_photo` is null/empty, use first element of `alt_photos` list as `photo_url`. One extra line in `_row_to_listing`. Do NOT do this for Redfin until the photo key instability is resolved.
- **D-05:** Diagnose Redfin photo key name with one-run logging (`print(raw_home.get("photos", {}).keys())`) before assuming current multi-shape handler covers it — this is a 30-second check, not optional

### No-photo placeholder design
- **D-06:** Replace the plain "No Photo Available" text div with: `Home` icon (28-32px, `lucide-react`) centered + "No Photo Available" text label below it
- **D-07:** Background stays `bg-slate-100`, icon and text color `text-slate-400` — matches current card aesthetic, looks intentional not broken
- **D-08:** The placeholder div must remain `h-52` (same height as the photo) to preserve card height consistency across the results grid

### Photo load failure UX
- **D-09:** Keep existing `onError` behavior — hides `<img>` and shows placeholder div. Current approach is correct; just ensure it works after the `referrerPolicy` attribute is added (should be transparent)
- **D-10:** Add `animate-pulse` to the placeholder div while image is potentially loading — signals something is coming. Implementation: placeholder shows with pulse animation by default; when `onLoad` fires, cancel the animation (or use CSS `[img loaded]` state). Keep it subtle — single pulse class, no custom keyframes.

### Claude's Discretion
- Exact Tailwind classes for `animate-pulse` integration (use standard Tailwind pulse, not custom keyframes)
- Whether to use `onLoad` to stop the pulse or just leave pulse running always for the placeholder
- Icon import placement in PropertyCard.jsx (add `Home` to existing lucide-react import line)

</decisions>

<specifics>
## Specific Ideas

- Research confirmed `referrerPolicy="no-referrer"` is the standard browser mechanism for this scenario (W3C Referrer Policy spec) — not a hack
- homeharvest's `alt_photos` field is `list[HttpUrl] | None` per installed source (`homeharvest/core/scrapers/models.py`) — safe to index with `[0]` after null check
- The `df.columns` diagnostic command: `print([c for c in df.columns if "photo" in c.lower()])` — run this during verification before assuming column name is stable

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PropertyCard component
- `frontend/src/components/PropertyCard.jsx` — current photo rendering logic, onError handler, placeholder div structure, lucide-react imports

### Photo providers
- `homesearch/providers/homeharvest_provider.py` — `_row_to_listing()` method where `photo_url` is extracted from `row.get("primary_photo")` and where `alt_photos` fallback should be added
- `homesearch/providers/redfin_provider.py` — multi-shape photo key handler in `_home_to_listing()`; inspect before touching

### Research
- `.planning/research/SUMMARY.md` §"Critical Pitfalls" — CDN 403 mechanism, Rich/questionary terminal corruption (not relevant to Phase 5 but documented), Redfin key instability, homeharvest column drift
- `.planning/research/ARCHITECTURE.md` — build order rationale and anti-patterns to avoid (proxy, post-fetch gallery)

### Model
- `homesearch/models.py` — `Listing.photo_url: Optional[str]` field definition

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Home` from `lucide-react` — already in npm deps, add to existing import in `PropertyCard.jsx`
- `onError` handler already in `PropertyCard.jsx` (line 33) — extend, don't replace
- `bg-slate-100`, `text-slate-400`, `h-52` — established placeholder classes already on the div

### Established Patterns
- Photo rendering pattern: `{photo_url ? <img .../> : null}` + separate placeholder div with `hidden`/`flex` toggle — keep this structure, just improve the placeholder content
- Provider field extraction: `row.get("field_name", fallback)` pattern used throughout `_row_to_listing()` — alt_photos fallback follows same pattern
- `onError` handler: `e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'` — fragile to DOM order changes; keep img and placeholder div adjacent

### Integration Points
- `photo_url` flows: homeharvest DataFrame → `_row_to_listing()` → `Listing.photo_url` → SQLite → `/api/search` response → `PropertyCard.jsx` `photo_url` prop
- `alt_photos` is available in the homeharvest DataFrame as a separate column but is NOT currently in the `Listing` model — alt fallback should be resolved in the provider (pick best URL, store as `photo_url`) rather than adding `alt_photos` to the model

</code_context>

<deferred>
## Deferred Ideas

- Alt photos gallery/carousel — significant React complexity, deferred to v2+
- Server-side photo proxy — explicitly rejected (ToS, SSRF, complexity)
- Redfin `alt_photos` fallback — defer until Redfin photo key instability is diagnosed and confirmed fixed in Phase 5

</deferred>

---

*Phase: 05-property-card-photos*
*Context gathered: 2026-03-25*
