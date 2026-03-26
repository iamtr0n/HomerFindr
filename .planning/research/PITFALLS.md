# Domain Pitfalls

**Domain:** v1.1 Polish & Verification — photo fetching, CLI progress bars, menu wiring
**Researched:** 2026-03-25
**Scope:** Integration pitfalls when adding these specific features to the existing HomerFindr v1.0 codebase

---

## Critical Pitfalls

Mistakes that cause hours of debugging, broken terminal state, or invisible regressions.

---

### Pitfall 1: Realtor.com CDN Returns 403 for Photo URLs When Served From localhost

**What goes wrong:** `homeharvest` populates `primary_photo` with URLs on `ap.rdcpix.com`. When a browser loads the React app from `http://127.0.0.1:8000` and the `<img>` tag requests those CDN URLs, the browser sends a `Referer: http://127.0.0.1:8000` header. The Realtor.com CDN enforces a referer allowlist — it only serves images to requests that look like they originate from `realtor.com`. The request is rejected with a 403.

**Why it looks like a data bug:** The `photo_url` field is non-empty in the API response. The `PropertyCard.jsx` `onError` handler (line 33) silently hides the broken image and shows the "No Photo Available" placeholder. No console error appears unless DevTools is open. The developer sees blank photo slots and suspects the scraper isn't returning photos.

**Consequences:** All Realtor.com property cards show "No Photo Available" even when photo data is present. The bug is invisible without DevTools Network inspection.

**Prevention:**
- Add `referrerPolicy="no-referrer"` to the `<img>` tag in `PropertyCard.jsx`. This suppresses the `Referer` header and bypasses the CDN hotlink check for static assets.
- Do not attempt to proxy images through the FastAPI backend — this violates Realtor.com ToS and adds backend complexity for no benefit.
- The fix is a one-line change to the `<img>` element in `PropertyCard.jsx`.

**Detection:** Open browser DevTools > Network > filter by Img. Look for 403 responses on `rdcpix.com` URLs. The `onError` handler fires silently — add a temporary `console.warn` to surface it during diagnosis.

**Phase:** Photo-fetching plan. Fix is frontend-only (`PropertyCard.jsx`), not a backend data problem.

---

### Pitfall 2: Redfin Photo URL Key Name Is Unstable Across API Response Shapes

**What goes wrong:** `redfin_provider.py` lines 112–117 handle three photo data shapes: a list of dicts with `"photoUrl"` key, a list of plain strings, and a plain string. The actual Redfin stingray API also returns dicts where the key is `"url"` instead of `"photoUrl"`, or where photo data is nested one level deeper. The `photos[0].get("photoUrl", "")` call returns `""` (not an exception) when the key name differs — producing silently empty `photo_url` strings on all Redfin listings.

**Why it happens:** The `redfin` package wraps an undocumented internal API. The existing multi-shape handling code in `_home_to_listing` is evidence this was already known at v1.0 time — but only the shapes encountered then were handled. The API response can vary by listing region, time of day, and search parameters.

**Consequences:** Redfin property cards show "No Photo Available" even when photos exist. Indistinguishable from the Realtor.com CDN issue without separate per-provider diagnosis.

**Prevention:**
- Before implementing photo display, diagnose the actual response shape for a Redfin search. Add a temporary `print(f"[Redfin] photos raw: {home_data.get('photos', 'MISSING')}")` to `_home_to_listing` for one search run.
- Broaden the photo key extraction to try `photoUrl`, `url`, `href`, `src` in order before giving up.
- Accept that Redfin photo coverage will be partial — use the placeholder gracefully.

**Detection:** All Redfin listings have empty `photo_url` in the API response JSON. Add `print([c for c in home_data if "photo" in c.lower()])` temporarily to surface the actual key names.

**Phase:** Photo-fetching plan — diagnosis step before implementation.

---

### Pitfall 3: Rich Live + questionary Terminal Corruption When Adding Progress Bars

**What goes wrong:** If any `Rich.Live` or `Rich.Progress` context is still active when a `questionary.select()` or `questionary.text()` prompt begins rendering, both fight for cursor control using incompatible ANSI escape sequences. The result: arrow-key prompts appear on top of the spinner frame, cursor positioning breaks, and the terminal enters a state where neither Rich nor questionary renders correctly. Ctrl+C is required to recover.

**The existing code already solves this correctly.** In `results.py` lines 55–65, a comment reads "CRITICAL: Rich Live must fully exit before any questionary prompt." The `with Live(...) as live:` block exits cleanly before any questionary call. The pitfall is that adding new `Progress` or `Live` contexts while extending `execute_search_with_spinner` will re-introduce the problem.

**Specific risk for v1.1:** Replacing the hand-rolled spinner loop with `rich.progress.Progress` — a natural upgrade — will break this invariant if the `Progress` context is opened inside the worker thread or if it outlives the current `with Live` boundary.

**Consequences:** Arrow-key navigation stops working after search results appear. The "Select a listing" questionary prompt renders incorrectly. Regression is obvious but the root cause (leaked Live context) is non-obvious.

**Prevention:**
- Keep a single `with Progress(...) as progress:` (or `with Live(...) as live:`) block in `execute_search_with_spinner`. Never open one inside `_search_worker` or anywhere the worker thread can reach.
- The worker thread must not write to the terminal at all — only the main thread's polling loop updates the display.
- The existing `thread.join(timeout=1.0)` call after the `with Live` block is load-bearing: it ensures the worker is done before any subsequent questionary call. Do not move it inside the `with` block.
- After any change, test: run a search from the TUI, let it complete, then verify arrow keys work correctly in the "Select a listing to open" questionary prompt.

**Detection:** After a search completes, the arrow-key listing selector renders garbled or does not respond to key presses. The Live context leaked.

**Phase:** CLI animation polish plan. This is the primary implementation risk for that plan.

---

### Pitfall 4: Rich Progress Task Lifecycle Race Condition

**What goes wrong:** When using `rich.progress.Progress` with a background thread, developers often call `progress.advance(task_id, 1)` from the worker thread after the main thread has already exited the `with Progress` block. This raises `RuntimeError` or silently does nothing depending on Rich version, and is a race condition — it manifests intermittently.

A variant: `progress.add_task(...)` called before `progress.start()` (when using manual lifecycle management), or `progress.stop()` called from the worker thread at the wrong time.

**Why it happens:** The search runs in a background thread (`_search_worker`) whose completion time relative to the main thread's `with Progress` exit is not deterministic. Any `advance()` call from the worker that races with the main thread's `__exit__` can produce the error.

**Prevention:**
- Use `with Progress(...) as progress:` exclusively — never call `.start()` / `.stop()` manually.
- For the simplest correct implementation: keep the progress display entirely in the main thread's polling loop (as the current hand-rolled spinner already does). Advance an indeterminate `SpinnerColumn` task based on elapsed time rather than worker callbacks. The worker thread never touches the `progress` object.
- If per-provider progress steps are desired (e.g., "Searching realtor... done"), pass a `threading.Event` per provider and advance from the main thread when the event is set — not from the worker.

**Detection:** `RuntimeError: progress is not started` in traceback. Happens intermittently; more likely on fast searches where the worker finishes before the first polling iteration completes.

**Phase:** CLI animation polish plan.

---

## Moderate Pitfalls

---

### Pitfall 5: homeharvest DataFrame Column Names Can Drift Between Package Versions

**What goes wrong:** `homeharvest_provider.py` accesses DataFrame columns by name: `row.get("primary_photo")` with `row.get("img_src")` as fallback. The `homeharvest` package has changed column names across minor versions — the existing multi-key fallback for `["street", "street_address"]` (lines 72–75) is direct evidence of a previous rename. The photo column is only guarded by two candidates. If `homeharvest` renames `primary_photo` to something else (e.g., `photo_url`, `main_image`), photo extraction silently returns empty strings.

**Why it matters for v1.1:** The photo-fetching plan assumes the scraper is already returning valid photo data. If the column name has drifted since v1.0, the plan's starting assumption is wrong and no amount of frontend work will fix it.

**Prevention:**
- During the verification phase, run one search and log actual column names: `print([c for c in df.columns if "photo" in c.lower()])`. Confirm `primary_photo` or `img_src` is present.
- This is a 30-second diagnostic that should precede any photo display work.

**Detection:** Zero `photo_url` values from Realtor.com results despite listings being returned. Narrow to column names before assuming a CDN issue.

**Phase:** End-to-end verification plan — run this check first.

---

### Pitfall 6: saved_browser.py Stale Search Object After Mutation

**What goes wrong:** `show_saved_searches_browser` fetches all searches at the top of its `while True` loop, then passes a specific `search` object into `_show_search_submenu`. After `_toggle_active` or `_rename_search` mutates the DB record, the in-memory `search` object is stale. On the next loop iteration the table is re-fetched (correct), but within a single submenu invocation, the stale object is still used.

**Current safety:** `_toggle_active` reads `search.is_active` to compute the new state — this is correct behavior for a toggle even with a stale object. `_rename_search` and `_delete_search` use only `search.id`, which never changes. Confirmation messages use the freshly-written value (e.g., `new_name.strip()`), not a read-back from the stale object. **No bug currently exists.**

**The risk:** If the submenu is extended (e.g., adding "Edit Criteria" or "Duplicate") and new code reads `search.name` or `search.criteria` after a rename/edit to display a confirmation, it will show stale data.

**Prevention:**
- No change needed now. Document this as known: the `search` object inside `_show_search_submenu` is a point-in-time snapshot.
- Any future actions that need current state must re-fetch: `db.get_saved_search(search.id)`.

**Phase:** Menu wiring verification — awareness, no fix required.

---

### Pitfall 7: questionary.select default= Type Mismatch Silently Picks First Item

**What goes wrong:** `questionary.select(..., default=<value>)` matches the default by equality against the `choices` list (or `Choice.value` for `Choice` objects). If types don't match — e.g., `default=25` (int) when choices are strings like `"25 miles"` — no default is highlighted and questionary silently selects the first item.

**Current exposure in `settings.py` line 138:** `default=d.get("radius", 25)` is an int; choices are `Choice(value=5)`, `Choice(value=10)`, etc. — also ints. This currently works. But `_show_search_defaults` also uses `default=d.get("listing_type", "sale")` with string choices — also correct.

**The risk for v1.1:** If the wizard or settings defaults are extended and a new `select` prompt uses a string choice list with an int default (or vice versa), the default highlight silently breaks — no exception, no warning, just wrong UX.

**Prevention:**
- When adding any new `questionary.select` with a `default=`, verify the default type matches the choice type. String choices → string default. `Choice(value=int)` → int default.
- Test the Settings > Search Defaults > Radius prompt: the saved radius value should be pre-highlighted. If the first item is always highlighted regardless of saved value, a type mismatch has been introduced.

**Detection:** Settings sub-menu always shows the first option highlighted regardless of what was previously saved.

**Phase:** Menu wiring verification.

---

### Pitfall 8: First-Run Wizard Is Skipped After a Partial Config Write

**What goes wrong:** `config_exists()` in `tui/config.py` checks whether the config file exists on disk. If the first-run wizard calls `save_config` partway through (e.g., after the SMTP step) and the user then Ctrl+Cs out, the config file exists on the next launch. `config_exists()` returns `True` and the wizard is skipped entirely — even though setup is incomplete.

**Why it matters for v1.1 verification:** The verification plan tests a "clean install" scenario. If the tester runs the wizard, Ctrl+Cs mid-way, and relaunches, they expect the wizard to re-appear. Instead they get the main menu with a broken or incomplete config.

**Prevention:**
- Test this scenario explicitly during verification: delete `~/.homesearch/config.json`, launch, enter the first-run wizard, Ctrl+C after the first question, relaunch.
- If the wizard is confirmed to skip: add a `"setup_complete": true` key that is only written at the very end of the first-run wizard. Change `config_exists()` to check for this key, not just file existence.

**Detection:** Delete config, launch, Ctrl+C mid-wizard, relaunch. Does the wizard re-appear?

**Phase:** End-to-end verification plan. Diagnose first; fix only if confirmed broken.

---

### Pitfall 9: Photo URLs Stored in SQLite Expire Over Time

**What goes wrong:** `photo_url` is scraped at search time and persisted in SQLite. Real estate CDN URLs for both Realtor.com and Redfin embed content-hash tokens or query parameters (e.g., `?w=1024&q=80&c=1`). These URLs are valid for days to weeks but can expire. A user who views the web dashboard weeks after their last search run may see all placeholder images even for listings that previously showed photos.

**Why this is acceptable:** The existing `onError` handler in `PropertyCard.jsx` (line 33) already falls back gracefully to "No Photo Available". No user-facing crash occurs.

**Prevention:**
- Do not attempt to re-fetch or proxy photo URLs on demand — disproportionate complexity for a personal tool.
- Document as expected behavior: photos are best-effort, captured at search time.
- For the verification checklist: test photo display immediately after a search run (should show photos) and note that stale results from weeks ago may show placeholders.

**Detection:** Stored results from a past search show all placeholder images. Inspect URL in DevTools — 404 confirms expiry rather than a CDN referer block (which returns 403).

**Phase:** No action needed. Document as known limitation in the verification checklist.

---

## Minor Pitfalls

---

### Pitfall 10: Rich console.status and Live Are Mutually Exclusive

**What goes wrong:** `console.status(...)` is a convenience wrapper around `Live`. Calling `console.status` while a `Live` context is active raises `RuntimeError: Only one live display may be active at a time`.

**Current exposure:** `wizard.py` line 254 uses `with console.status("Discovering ZIP codes...")` during the wizard flow. `results.py` uses `with Live(...)` during search execution. These run at different stages so there is no current conflict.

**The risk for v1.1:** If ZIP discovery is moved inside the same animated block as the search execution progress bar (e.g., to show a single unified loading screen), both will be active simultaneously and the error will fire.

**Prevention:**
- Keep the ZIP discovery `console.status` separate from the search execution `with Live/Progress` block.
- If a unified display is desired, replace both with a single `with Progress(...) as progress:` instance that has separate tasks for each stage.

**Detection:** `RuntimeError: Only one live display may be active at a time` at runtime during a search. Happens immediately and deterministically — easy to diagnose.

**Phase:** CLI animation polish plan. Awareness only — no current conflict.

---

### Pitfall 11: CORS Wildcard + Future Photo Proxy Endpoint

**What goes wrong:** `routes.py` lines 31–35 sets `allow_origins=["*"]`. For a local-only tool this is acceptable. However, if a `/api/proxy-photo?url=...` endpoint were added to work around CDN hotlink issues, the wildcard CORS policy would mean any page open in the browser could use it to fetch arbitrary URLs through the local server — a potential SSRF vector.

**Prevention:**
- Do not add a photo proxy endpoint. The `referrerPolicy="no-referrer"` fix on the `<img>` tag is the correct approach and requires no backend change.
- If a proxy is ever considered, restrict CORS to specific local origins first.

**Phase:** Photo-fetching plan. Prevention: choose the frontend-only fix (Pitfall 1).

---

### Pitfall 12: daemon Thread Hang on Provider Network Timeout

**What goes wrong:** In `results.py`, the search runs in a `threading.Thread(daemon=True)`. If `run_search` hangs indefinitely (e.g., `homeharvest.scrape_property` blocking on a slow network request with no timeout), `done_event` is never set. The main thread's `with Live` polling loop runs forever — the spinner animates forever and the TUI appears hung.

**Why it matters for verification:** The verification phase tests against real network conditions. A slow or unresponsive Realtor.com endpoint will expose this.

**Prevention:**
- The existing `time.sleep(1.5)` per ZIP in `homeharvest_provider.py` provides implicit progress but not a hard timeout.
- For the verification checklist: note the maximum expected wait time for a typical search (e.g., 20 ZIPs × 1.5s = 30 seconds). If a search runs longer than 2× this, assume a hang.
- A simple guard: track total elapsed time in the main thread polling loop. If elapsed exceeds a configured maximum (e.g., 5 minutes), break out of the loop and display a timeout message. This is a low-priority hardening task, not a blocker.

**Detection:** Spinner animates indefinitely. Ctrl+C exits cleanly (caught by `KeyboardInterrupt` in `run_menu_loop`), confirming the main thread is alive but waiting.

**Phase:** CLI animation polish / verification. Low priority.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Photo display in React | Realtor.com CDN 403 (Pitfall 1) | Add `referrerPolicy="no-referrer"` to `<img>` in `PropertyCard.jsx` |
| Photo data from Redfin | Unstable response key name (Pitfall 2) | Debug-log raw photo shape before assuming the key name |
| Photo data from homeharvest | Column name drift between versions (Pitfall 5) | Log `[c for c in df.columns if "photo" in c.lower()]` during verification |
| CLI progress bars | Rich Live + questionary terminal corruption (Pitfall 3) | Keep single `with Live/Progress` block; worker thread never touches the display |
| CLI progress bars | Progress task lifecycle race (Pitfall 4) | Use context manager form only; advance from main thread, not worker |
| CLI progress bars | Nested console.status + Live conflict (Pitfall 10) | Keep ZIP discovery status separate from search execution Live block |
| Menu wiring verification | Stale search object post-mutation (Pitfall 6) | Awareness only; current code is safe; do not read-back from stale object |
| Menu wiring verification | questionary default= type mismatch (Pitfall 7) | Verify radius default highlights correctly in Settings after a save |
| End-to-end verification | First-run wizard skips after partial config (Pitfall 8) | Test Ctrl+C mid-wizard scenario explicitly |
| End-to-end verification | Stale DB photo URLs show as placeholder (Pitfall 9) | Document as known; test photos immediately after a search run |
| Photo proxy (avoid this approach) | CORS wildcard SSRF exposure (Pitfall 11) | Use frontend-only `referrerPolicy` fix instead |

---

## Sources

- Source code analysis (first-party, HIGH confidence): `homesearch/providers/homeharvest_provider.py`, `homesearch/providers/redfin_provider.py`, `homesearch/tui/results.py`, `homesearch/tui/wizard.py`, `homesearch/tui/saved_browser.py`, `homesearch/tui/settings.py`, `homesearch/tui/menu.py`, `frontend/src/components/PropertyCard.jsx`, `homesearch/api/routes.py`
- Rich Live/Progress mutual exclusivity: https://rich.readthedocs.io/en/stable/live.html (HIGH confidence, official docs)
- Rich threading behavior and Live context exclusivity: confirmed from existing code comments in `results.py` ("CRITICAL: Rich Live must fully exit before any questionary prompt") — HIGH confidence
- Realtor.com CDN hotlink protection via Referer: MEDIUM confidence — standard CDN protection pattern; the `referrerPolicy="no-referrer"` mitigation is a documented browser spec behavior, not a workaround
- Redfin stingray API response shape instability: MEDIUM confidence — the existing multi-shape handling in `_home_to_listing` confirms this was encountered at v1.0 time
- homeharvest column name drift: MEDIUM confidence — the `["street", "street_address"]` multi-key fallback in `_row_to_listing` is direct evidence of a prior rename
- questionary `default=` type matching: MEDIUM confidence — confirmed from reading `settings.py` usage and questionary source behavior; no official doc citation found
