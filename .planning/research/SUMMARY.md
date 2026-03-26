# Project Research Summary

**Project:** HomerFindr — v1.1 Polish & Verification
**Domain:** Local-first CLI + web dashboard real estate aggregator
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

HomerFindr v1.1 is a targeted polish-and-verification milestone, not a feature expansion. The v1.0 codebase delivered a complete layered architecture — arrow-key TUI, FastAPI backend, React web dashboard, provider abstraction, SQLite persistence — and v1.1 adds three narrow improvements on top: property card thumbnail photos visible in the browser, richer CLI progress feedback during searches, and confirmed-working Settings/Saved Searches menu paths. All three features use capabilities already present in the installed package set; zero new dependencies are required for any of them.

The recommended approach is surgical. The photo display gap is not a data problem — `Listing.photo_url` is already populated by both providers — it is a browser referer header problem solvable with a one-line `referrerPolicy="no-referrer"` attribute on the `<img>` tag in `PropertyCard.jsx`. The CLI progress upgrade replaces a hand-rolled braille spinner in `tui/results.py` with `rich.progress.Progress` (already installed at >=13.7.0) using indeterminate mode (`total=None`) or per-ZIP `add_task`/`advance` once ZIP count is known. Settings and Saved Searches menu wiring is confirmed complete by direct code inspection; v1.1's job is runtime verification and edge-case patching, not new wiring.

The primary risk is terminal state corruption: `Rich.Live` and `questionary` fight for cursor control if a `Live`/`Progress` context is not fully exited before any `questionary` prompt begins. The existing code respects this invariant via a documented comment in `results.py`; any progress bar refactoring must maintain it. Secondary risks are CDN-level photo blocking (mitigated by `referrerPolicy`) and unstable Redfin photo response key names (mitigated by diagnostic logging before touching any code). Both risks are well-understood and have clear, low-effort prevention strategies.

---

## Key Findings

### Recommended Stack

The v1.0 stack is validated and unchanged for v1.1. Zero new Python packages and zero new npm packages are needed.

**Core technologies (already installed, no changes):**
- `rich>=13.7.0`: `rich.progress.Progress` API confirmed available from installed source at `.venv/lib/python3.11/site-packages/rich/progress.py` — `SpinnerColumn`, `TextColumn`, `TimeElapsedColumn`, `BarColumn`, `MofNCompleteColumn`, `add_task()`, `advance()`, `transient` param all present
- `questionary>=2.1.1`: arrow-key prompts — must be called only after `Rich.Live`/`Progress` context has fully exited; this invariant is already established in the codebase
- `homeharvest>=0.4.0`: `Description.primary_photo: HttpUrl | None` confirmed in installed source (`homeharvest/core/scrapers/models.py`); `"primary_photo"` column confirmed in `utils.py` `ordered_properties`
- `httpx>=0.27.0`: available if a server-side photo proxy were needed, but the `referrerPolicy` frontend fix makes it unnecessary
- `lucide-react` (already in npm deps): `Home` icon available for the styled "No Photo" placeholder

### Expected Features

**Must have (table stakes):**
- Property card thumbnail photos rendering in the web dashboard — every reference site (Zillow, Redfin) shows photo thumbnails as the primary visual element; missing photos read as a broken prototype
- CLI search progress with ZIP-level or per-provider granularity — multi-ZIP searches take 30–90+ seconds; a static spinner with no progress indication reads as frozen
- Settings and Saved Searches sub-menus that navigate without exceptions — broken navigation in the main menu loop breaks the core UX contract
- Saved Searches "Run Now" that executes a real search and updates `last_run_at` — silent failure here makes the feature non-functional in practice
- Clean install verification on a fresh terminal session — the primary distribution path is `pipx install . → homerfindr`; must be shareable

**Should have (differentiators):**
- Per-ZIP progress bar showing "Searching realtor.com [ZIP 3/7]..." — transforms wait time into visible, trust-building feedback
- Styled "No Photo" placeholder using `lucide-react` `Home` icon instead of a grey `bg-slate-100` rectangle — makes the fallback look intentional, not broken
- `transient=True` on the `Progress` instance — bar clears on completion, keeping the terminal output clean for the results table
- End-to-end verification checklist as a living `.planning/` artifact — turns "feels done" into "verified done" for every future release

**Defer to v2+:**
- Alt photos gallery/carousel — `homeharvest` returns `alt_photos` but a carousel adds significant React complexity for marginal v1.1 value
- Photo caching or server-side proxy — browser handles caching naturally; a proxy adds ToS risk, SSRF exposure, and maintenance overhead
- Automated pytest suite for scraper paths — manual verification checklist covers the same acceptance surface at far lower cost for this milestone
- New search criteria fields or new providers — touches schema, providers, API, and frontend simultaneously; out of scope for a polish release

### Architecture Approach

The v1.1 changes are confined to the surface layer. The existing architecture (Models → Config → Database → Providers → Services → API/CLI → Frontend) remains completely unchanged. Three surface components receive targeted edits; the service layer, database layer, and all providers are untouched.

**Major components receiving changes:**
1. `frontend/src/components/PropertyCard.jsx` — add `referrerPolicy="no-referrer"` to `<img>` tag; polish "No Photo" placeholder with `Home` icon from lucide-react
2. `homesearch/tui/results.py` — replace manual braille spinner with `rich.progress.Progress`; maintain the existing `with Progress` context manager boundary strictly before any questionary call
3. `homesearch/tui/settings.py` + `homesearch/tui/saved_browser.py` — runtime verification; patch any edge cases surfaced (empty SMTP config KeyError, stale list after delete, first-run re-entry after partial config write)

**What does NOT change:** `search_service.py`, `database.py`, all providers, `models.py`, `api/routes.py`, all other frontend components.

### Critical Pitfalls

1. **Realtor.com CDN returns 403 for photo URLs from localhost** — the `Referer: http://127.0.0.1:8000` header sent by the browser triggers the CDN hotlink allowlist. Fix with `referrerPolicy="no-referrer"` on the `<img>` tag in `PropertyCard.jsx`. Do not proxy images through FastAPI (ToS risk, SSRF exposure with existing wildcard CORS policy, unnecessary complexity).

2. **Rich Live + questionary terminal corruption when adding progress bars** — if any `Rich.Live`/`Progress` context is active when a `questionary.select()` prompt begins, both fight for cursor control and the terminal breaks. The existing code already solves this (`results.py` has a documented "CRITICAL" comment). Any refactoring must keep the single `with Progress(...) as progress:` block and ensure the worker thread never touches the `Progress` object.

3. **Rich Progress task lifecycle race condition** — `progress.advance(task_id)` called from the worker thread after the main thread exits the `with Progress` block raises `RuntimeError` intermittently. Use context manager form only; advance from the main thread via `threading.Event` signals, not directly from the worker.

4. **Redfin photo response key name instability** — the `redfin` package wraps an undocumented API; the key for photo data has varied (`"photoUrl"` vs `"url"` vs `"href"`). The existing multi-shape handling code in `_home_to_listing` is evidence this was already encountered. Before assuming photos work, add one-run diagnostic logging to confirm the actual key name.

5. **homeharvest DataFrame column name drift** — `homeharvest_provider.py` uses `row.get("primary_photo")` which is confirmed correct from installed source, but minor version bumps have caused column renames before (the `["street", "street_address"]` multi-key fallback is direct evidence). Run `print([c for c in df.columns if "photo" in c.lower()])` during Phase 1 verification before assuming the column name is stable.

---

## Implications for Roadmap

Based on combined research, the natural phase structure follows feature independence and risk ordering: diagnose first, then fix the highest-visibility gap (photos), then polish the UX (progress bars), then verify the full integrated system.

### Phase 1: Photo Pipeline Verification and Fix

**Rationale:** Photos are the highest-visibility gap and the fix is the smallest change (one attribute on one JSX element), but diagnosis must come first. Pitfall 5 (homeharvest column name drift) means "no photos" could be a data gap rather than a CDN referer issue — rule that out in minutes before touching frontend code. Sequence: (1) run a real search, log `df.columns`, confirm `photo_url` is populated in SQLite, (2) open DevTools Network tab and check for 403s on `rdcpix.com` URLs, (3) add `referrerPolicy="no-referrer"`, (4) polish the "No Photo" placeholder.
**Delivers:** Property card thumbnail photos rendering in the web dashboard for both Realtor.com and Redfin listings; styled "No Photo" placeholder with `Home` icon for listings without photos
**Addresses:** Table stakes — property card thumbnails; differentiator — intentional placeholder design
**Avoids:** Pitfall 1 (CDN 403 — frontend `referrerPolicy` fix), Pitfall 2 (Redfin key instability — diagnostic logging first), Pitfall 5 (homeharvest column drift — df.columns check first), Pitfall 11 (SSRF from proxy approach — explicitly not using a proxy)

### Phase 2: CLI Progress Bar Polish

**Rationale:** The spinner upgrade is a contained change to `tui/results.py` with a well-understood pattern and verified API. Doing it after photos keeps the change surface minimal and keeps the terminal corruption pitfall (Pitfall 3) isolated to this phase where it can be specifically tested. The Rich Progress API is fully confirmed from installed source — no guesswork.
**Delivers:** Per-ZIP progress bar during CLI searches using `rich.progress.Progress`; `transient=True` removes bar on completion; result is a clean terminal with results table following immediately after search
**Uses:** `rich>=13.7.0` — `Progress`, `SpinnerColumn`, `TextColumn`, `BarColumn`, `MofNCompleteColumn`, `TimeElapsedColumn`; all confirmed present in installed source
**Avoids:** Pitfall 3 (Rich Live + questionary corruption — single `with Progress` block, worker never touches progress object), Pitfall 4 (task lifecycle race — context manager form only, main-thread advance via events), Pitfall 10 (nested `console.status` + `Live` conflict — keep ZIP discovery status separate from search execution block)

### Phase 3: Settings and Saved Searches Wiring Verification

**Rationale:** This is primarily a verification and edge-case patching phase. All handler dispatch is confirmed correct by code inspection (`menu.py` dispatches to `settings.py` and `saved_browser.py` correctly; both modules implement expected sub-menus). The work is walking every sub-menu path on a real run, surfacing runtime edge cases, and patching them. Sequenced after Phases 1 and 2 because it tests the full integrated system.
**Delivers:** All four main menu branches (New Search, Saved Searches, Settings, Launch Web UI) confirmed working end-to-end with no exceptions; "Run Now" updates `last_run_at`; delete refreshes list without restart; SMTP wizard handles empty/default config gracefully
**Avoids:** Pitfall 6 (stale search object post-mutation — awareness only, current code is safe, document for future changes), Pitfall 7 (questionary `default=` type mismatch — validate radius pre-highlighting in Settings after save), Pitfall 8 (first-run wizard skip after partial config write — test Ctrl+C mid-wizard scenario explicitly)

### Phase 4: End-to-End Install Verification

**Rationale:** The final gate before calling v1.1 shipped. Tests `pipx install . → homerfindr` on a clean terminal session, walks every CLI and web UI path as a user would, confirms photos render immediately after a fresh search run, and produces the verification checklist as a living artifact for future releases.
**Delivers:** Documented and executed end-to-end verification checklist covering install, all CLI menu paths, all web UI paths, photo verification, SQLite state checks, and "Run Now" timestamp verification
**Avoids:** Pitfall 8 (first-run wizard edge cases — explicit clean-install test), Pitfall 9 (stale photo URL expectation — document that photos are best-effort, captured at search time; test immediately after run, not from stale results)

### Phase Ordering Rationale

- Photos first because the diagnosis step (log column names, inspect network tab) informs whether the frontend fix is sufficient or whether provider code also needs attention — this shapes the scope of all subsequent work
- Progress bar second because it is the highest-risk change (terminal state corruption regression) and benefits from being isolated in its own phase with targeted testing
- Settings verification third because it tests the integrated system with all prior changes in place
- Install verification last because it validates the full artifact produced by all prior phases; the checklist becomes a living document for future releases

### Research Flags

Phases with well-documented patterns (no additional research needed):
- **Phase 1:** `referrerPolicy="no-referrer"` is documented browser spec behavior (W3C Referrer Policy). Rich photo pipeline confirmed from installed package source. Standard patterns.
- **Phase 2:** `rich.progress.Progress` API confirmed from installed source at `.venv/.../rich/progress.py`. Pattern is established and tested in project already.
- **Phase 3:** All menu handler dispatch confirmed by direct code inspection. No research needed — only runtime execution and edge-case patching.
- **Phase 4:** Manual verification checklist. No research needed — only execution discipline and documentation.

No phases require a `/gsd:research-phase` deeper dive during planning. The research is complete and source-verified.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies confirmed by tracing all three features to already-installed packages; verified from `.venv` source |
| Features | HIGH | All three feature pipelines verified from installed package source code and first-party codebase inspection; feature gaps confirmed by direct code inspection |
| Architecture | HIGH | No architectural changes; surface-layer edits only; component boundaries confirmed by existing codebase analysis; no new patterns required |
| Pitfalls | MEDIUM-HIGH | Rich/questionary terminal corruption and progress race conditions are HIGH confidence (confirmed from existing code comments and official docs); CDN referer behavior is MEDIUM (standard pattern, not officially documented for these specific CDNs) |

**Overall confidence:** HIGH

### Gaps to Address

- **Realtor.com photo coverage rate per search area:** Unknown what percentage of active listings will have `primary_photo` populated. Must be validated during Phase 1 diagnosis. If coverage is low, the `alt_photos` fallback (one-line improvement in `homeharvest_provider.py` using the confirmed `alt_photos` field from installed source) should be added.

- **Redfin photo key name in current live API response:** The `redfin` package wraps an undocumented API. The actual key used (`photoUrl` vs `url` vs `href`) must be confirmed by diagnostic logging during Phase 1 before assuming the current multi-shape handler covers it. This is a 30-second check; do not skip it.

- **`referrerPolicy="no-referrer"` effectiveness for Realtor.com CDN specifically:** MEDIUM confidence that suppressing the `Referer` header bypasses the CDN allowlist check. This is the standard browser mechanism for this exact scenario, but CDN-specific behavior is not officially documented by Realtor.com. Validate in DevTools Network tab during Phase 1 before closing the work.

- **First-run wizard Ctrl+C resilience:** Confirmed as a risk worth testing but not confirmed as a current bug. Test the scenario in Phase 3; add `"setup_complete": true` key (written only at wizard end) only if confirmed broken.

---

## Sources

### Primary (HIGH confidence)
- `/Users/iamtron/Documents/GitHub/HomerFindr/.venv/lib/python3.11/site-packages/homeharvest/utils.py` — `ordered_properties` confirms `"primary_photo"` column name; `process_result()` confirms extraction logic
- `/Users/iamtron/Documents/GitHub/HomerFindr/.venv/lib/python3.11/site-packages/homeharvest/core/scrapers/models.py` — `Description.primary_photo: HttpUrl | None` and `alt_photos: list[HttpUrl] | None` confirmed
- `/Users/iamtron/Documents/GitHub/HomerFindr/.venv/lib/python3.11/site-packages/rich/progress.py` — `Progress`, `add_task()`, `advance()`, `transient` parameter confirmed in installed version
- Codebase: `homesearch/providers/homeharvest_provider.py`, `homesearch/providers/redfin_provider.py`, `homesearch/tui/results.py`, `homesearch/tui/menu.py`, `homesearch/tui/settings.py`, `homesearch/tui/saved_browser.py`, `frontend/src/components/PropertyCard.jsx`, `homesearch/models.py`, `homesearch/database.py`, `homesearch/api/routes.py`
- [Rich Progress Display Documentation](https://rich.readthedocs.io/en/latest/progress.html) — `SpinnerColumn`, indeterminate mode via `total=None`, `transient`
- [Rich Live Documentation](https://rich.readthedocs.io/en/stable/live.html) — Live context mutual exclusivity rule

### Secondary (MEDIUM confidence)
- [HomeHarvest GitHub — Bunsly/HomeHarvest](https://github.com/Bunsly/HomeHarvest) — `img_src` and `alt_photos` field schema
- Realtor.com CDN hotlink protection via `Referer` header — standard CDN protection pattern; `referrerPolicy="no-referrer"` is documented W3C browser spec behavior
- Redfin stingray API response shape instability — inferred from existing multi-shape handling code in `_home_to_listing` (direct evidence of prior API variance encountered during v1.0 development)
- [Uvicorn background thread pattern — bugfactory.io](https://bugfactory.io/articles/starting-and-stopping-uvicorn-in-the-background/) — already implemented in v1.0's web launcher

### Tertiary (LOW confidence)
- questionary `default=` type matching behavior — confirmed from reading `settings.py` usage patterns; no official doc citation found

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
