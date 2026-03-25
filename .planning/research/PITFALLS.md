# Domain Pitfalls

**Domain:** Python CLI polishing + web UI redesign (home search aggregator)
**Researched:** 2026-03-25

---

## Critical Pitfalls

Mistakes that cause rewrites, blocked features, or shipped regressions.

---

### Pitfall 1: Rich and InquirerPy Outputting to Conflicting Streams

**What goes wrong:** Rich uses its own `Console` object that writes to `sys.stdout` and detects terminal capabilities (color support, width, TTY). InquirerPy (via `prompt_toolkit`) also takes over terminal input/output directly. When both run simultaneously or in alternating sequence without explicit coordination, you get interleaved output corruption: half-rendered progress bars, blank lines eating the menu, or the cursor left in a broken state after a prompt.

**Why it happens:** Rich's Live display holds the terminal in a managed state. Any other write to stdout during a Live context — including prompt_toolkit's own rendering — breaks Rich's internal line-count bookkeeping. Rich also does terminal-capability detection at construction time; if InquirerPy initializes first and wraps stdin/stdout, Rich may detect non-interactive mode and disable all color/formatting.

**Consequences:** The CLI looks broken on first launch. ANSI escape sequences leak into output. Progress bars don't clear. The house-loading animation fires before or after menus in a way that corrupts the screen.

**Prevention:**
- Never run Rich's `Live` or `Progress` context at the same time as an InquirerPy prompt. Exit the Live context fully before launching any interactive prompt.
- Always construct a single `Console` instance at startup and pass it everywhere — do not let Rich auto-detect and create one inside each function call.
- Verify with `console.is_terminal` at startup; if False (e.g., output is piped), disable all interactive features gracefully.
- Test the full CLI flow in both iTerm2 and macOS Terminal.app. They handle ANSI differently.

**Detection:** Cursor appears in the wrong position after a menu selection. Subsequent `console.print()` calls produce blank lines. ASCII art appears mid-menu.

**Phase:** CLI UX overhaul phase (interactive menus + ASCII art).

---

### Pitfall 2: Blocking HTTP Scraping Freezes the Interactive CLI

**What goes wrong:** Both `homeharvest` and `redfin` providers are fully synchronous and call `time.sleep()` internally (1.5–2 seconds per ZIP code). When a user triggers a search from the interactive CLI menu, the entire process blocks — arrow-key menus stop responding, Rich's animated loading spinner freezes, and the terminal appears hung.

**Why it happens:** The existing CONCERNS.md documents this: searches over 50 ZIP codes can take 175+ seconds. The current FastAPI route runs these synchronously. The CLI, which calls the same service layer, inherits the same blocking behavior.

**Consequences:** Users think the app crashed. Ctrl+C during a blocking scrape may leave SQLite in a dirty state or leave a half-written database record.

**Prevention:**
- Wrap the search call in a `threading.Thread` when invoked from the CLI. Use a `threading.Event` to signal completion.
- Show a Rich `Live` spinner that updates on the main thread while the search thread runs in the background.
- Provide explicit "press Q to cancel" escape during long searches.
- Cap ZIP code batch size to a configurable maximum (e.g., 20 ZIPs) for interactive CLI use; warn the user if the radius would yield more.

**Detection:** Spinner animation freezes the moment a search starts. Terminal stops accepting keystrokes.

**Phase:** CLI UX overhaul phase — must address before the search wizard is usable.

---

### Pitfall 3: macOS .app Packaging Fails on Apple Silicon / Gatekeeper

**What goes wrong:** Python apps packaged with py2app or PyInstaller frequently fail on Apple Silicon Macs unless every bundled C extension is compiled as `arm64` or `universal2`. The hardened runtime required by Gatekeeper notarization is incompatible with cffi/ctypes unless specific entitlements are declared. The result: the `.app` opens fine in development but fails with a "killed" or "not opened" Gatekeeper error on another machine.

**Why it happens:**
- Many Python packages ship only `x86_64` wheels. A `universal2` `.app` bundle that includes an `x86_64`-only `.dylib` will be rejected by codesign validation.
- PyInstaller requires `com.apple.security.cs.allow-unsigned-executable-memory` entitlement. Without it, the hardened runtime kills the process on launch.
- Signing with `--deep` (the intuitive approach) does not work correctly for PyInstaller bundles; each binary inside must be signed inside-out.
- Gatekeeper quarantine flag is set on downloaded `.app` files; unsigned or improperly signed apps are silently blocked.

**Consequences:** The `.app` works perfectly in the developer's environment but cannot be distributed or opened on another machine without terminal workarounds.

**Prevention:**
- **Prefer a shell script launcher over a full `.app` bundle for personal/friends-and-family distribution.** A `~/.local/bin/homerfindr` shell script that activates the virtualenv and runs the CLI is simpler, more reliable, and avoids the entire Gatekeeper/notarization problem.
- If a real `.app` is needed: use PyInstaller (not py2app), sign with `arch -arm64` explicitly, declare all required entitlements in a `.entitlements` plist, and sign each `.dylib`/`.so` individually before signing the bundle.
- Test on a separate machine not used for development before declaring packaging complete.

**Detection:** Works locally but shows "cannot be opened because the developer cannot be verified" on another Mac. Or the app opens and immediately quits silently.

**Phase:** Desktop packaging phase. Recommend deferring full `.app` to a later milestone; ship the global CLI command first.

---

### Pitfall 4: The `previewSearch` Double-`/api` Prefix Bug Blocks the Core Search Flow

**What goes wrong:** The existing codebase has a documented bug (CONCERNS.md) where the preview endpoint is defined at `@app.post("/api/search/preview")` in routes.py, while `api.js` prepends the `/api` base, resulting in a 404 on every preview search. Users clicking Search get no results and no error message (errors are `console.error` only).

**Why it matters for the redesign:** Any web UI redesign that keeps the existing `api.js` client and routes.py as-is will inherit this broken search flow. Building new property card components on top of a broken search path wastes implementation time.

**Prevention:**
- Fix the route prefix before touching the web UI. Either remove the `/api` prefix from the route definition (making it `@app.post("/search/preview")`) so the Vite proxy handles it correctly, or strip the `/api` base prefix from `api.js`.
- Add a basic smoke test: does clicking Search return results? Verify before starting the visual redesign.

**Detection:** Browser network tab shows 404 on `/api/api/search/preview`. No results appear after clicking Search.

**Phase:** Must be fixed in the first task of the web UI redesign phase, before any frontend work.

---

### Pitfall 5: Provider Scraping Can Be Blocked Without User Feedback

**What goes wrong:** Both `homeharvest` and `redfin` wrap unofficial internal APIs. Redfin uses bot detection and IP rate limiting. HomeHarvest returns a 403 Forbidden when blocked. The current codebase catches errors in `run_search` and swallows them — the user sees an empty result set with no indication that a provider was blocked.

**Why it happens:** Rate limiting is intermittent and session-dependent. A search that works fine 10 times may hit a block on the 11th. The CLI's new animated search experience makes this worse: the spinner completes "successfully" but returns zero homes.

**Consequences:** User concludes the tool is broken or there are no homes matching criteria, when the real problem is a temporary block. Trust in the tool erodes.

**Prevention:**
- Distinguish `ProviderBlockedError` from legitimate zero-result responses. Log the HTTP status code.
- Surface a clear CLI message: "Realtor.com returned a 403 — you may have been rate-limited. Try again in a few minutes."
- Implement per-provider health checks that can be displayed in a CLI status panel.
- Do not retry automatically in a loop — this deepens the block.

**Detection:** Zero results on searches that previously returned data. No error surfaced to the user.

**Phase:** CLI search wizard phase; also applies to web UI search flow.

---

## Moderate Pitfalls

---

### Pitfall 6: ASCII Art Breaks on Narrow Terminals or Non-UTF-8 Locales

**What goes wrong:** pyfiglet renders ASCII art at a fixed character width determined by the font. Most figlet fonts render "HomerFindr" at 60–90 characters wide. On a terminal narrower than the art (e.g., a split-pane tmux window, or a 80-column macOS Terminal.app default), the art wraps mid-character, producing visual noise. On terminals with non-UTF-8 locale (`LANG=C`), Unicode block characters used by some `art` library fonts produce `UnicodeEncodeError` at startup.

**Prevention:**
- Query terminal width with `os.get_terminal_size().columns` before rendering. If width < art width, fall back to a shorter single-line logo or plain text header.
- Use only ASCII-safe figlet fonts (avoid fonts that use Unicode box-drawing characters). The standard `slant`, `banner3`, or `doom` fonts are safe.
- Wrap the art render in a try/except `UnicodeEncodeError` and fall back gracefully.
- Test the splash screen in a narrow terminal (60 columns) before shipping.

**Detection:** Art wraps visually at startup. `UnicodeEncodeError` traceback on some systems.

**Phase:** ASCII art / splash screen implementation.

---

### Pitfall 7: Global CLI Command Breaks When Homebrew Updates Python

**What goes wrong:** Installing `homerfindr` globally via `pip install -e .` or a symlink to a venv's Python puts a hard path to a specific Python binary in the script shebang. When Homebrew updates Python (which it does automatically as a dependency of other packages), the shebang path becomes stale. The command silently fails or raises `No module named homesearch`.

**Prevention:**
- Use `pipx install .` for global CLI installation. pipx manages isolated environments per app and handles Python upgrades gracefully.
- Document `pipx` as the recommended install method in the project README.
- Avoid `pip install -e .` into the system Python or a Homebrew Python for global commands.
- The shell wrapper approach (a `homerfindr` shell script in `~/.local/bin` that activates the project venv) is brittle for the same reason — use pipx instead.

**Detection:** `homerfindr` command works, then starts failing after a macOS update or Homebrew upgrade.

**Phase:** Desktop packaging / global command phase.

---

### Pitfall 8: Tailwind v3 vs v4 Dark Mode and Configuration Mismatch

**What goes wrong:** The existing React/Vite frontend uses Tailwind CSS (version not pinned in the known codebase state). Tailwind v4, released in 2025, changed the configuration format significantly — `tailwind.config.js` is deprecated in favor of CSS `@import` directives. The dark mode strategy changed between v3.4.1 and v4. If the redesign adds new Tailwind config without pinning the version, a `npm install` on a fresh machine may pull v4, breaking all existing dark mode classes and custom configuration.

**Prevention:**
- Pin the Tailwind version explicitly in `package.json` (`"tailwindcss": "^3.4.x"`) before starting the redesign.
- Audit the current Tailwind version in use and commit it before any styling work.
- If upgrading to v4 is desired, do it as a standalone commit before any design work, not interleaved.

**Detection:** `dark:` classes stop applying after a fresh `npm install`. Custom colors from `tailwind.config.js` are ignored.

**Phase:** Web UI redesign phase — check on day one.

---

### Pitfall 9: `sortedResults` Duplication Creates Silent UI Inconsistency

**What goes wrong:** CONCERNS.md documents that the sort function is copy-pasted identically into `NewSearch.jsx` and `SearchResults.jsx`. The web UI redesign will touch both pages for visual updates. If sort logic is updated in one file and not the other (easy mistake during a large redesign), users see different sort behavior on the same data depending on which page they're on.

**Prevention:**
- Extract to `frontend/src/utils/sortListings.js` as the first task of the web UI phase, before touching any visual code.
- This is a small refactor (30 minutes) with a large safety payoff.

**Detection:** Sort order differs between the New Search results view and the Saved Search results view.

**Phase:** Web UI redesign phase — pre-flight cleanup step.

---

### Pitfall 10: SMTP Wizard Stores Credentials in Memory Across CLI Sessions

**What goes wrong:** The SMTP setup wizard (interactive arrow-key flow for configuring email) will collect the SMTP password via InquirerPy's password prompt. If the wizard writes this to the `.env` file directly (the natural approach), it overwrites any existing `.env` content, may introduce encoding issues if the password contains special characters, and creates a second code path for managing `.env` that can diverge from the documented setup.

**Prevention:**
- Use Python's `python-dotenv` `set_key()` function to update individual keys in `.env` without overwriting the file.
- Mask the password in CLI display (InquirerPy's `PasswordPrompt` handles this by default).
- Show a confirmation message that the key was written, but never echo the value back.
- Validate SMTP credentials immediately after saving by attempting a test connection — do not wait for the user to trigger a report.

**Detection:** SMTP wizard completes but the next report send fails. Or the `.env` file loses other keys after the wizard runs.

**Phase:** SMTP wizard / settings phase.

---

### Pitfall 11: FastAPI Startup Event Deprecation Warning Clutters CLI Output

**What goes wrong:** CONCERNS.md flags that `@app.on_event("startup")` is deprecated in FastAPI in favor of the `lifespan` context manager. When the CLI launches the FastAPI server in a subprocess, deprecation warnings from the server leak into the CLI's stdout if not suppressed. These warnings break Rich's rendering of the UI because unexpected lines appear before the Rich console takes control.

**Prevention:**
- Fix the `lifespan` migration before building the CLI launcher that starts the server.
- When launching FastAPI as a subprocess from the CLI, redirect uvicorn's stdout/stderr to a log file or suppress it: `stdout=subprocess.DEVNULL` or route to a `logging.FileHandler`.
- Never let the subprocess share the parent process's stdout when Rich has control of the terminal.

**Detection:** Deprecation warning text appears over the ASCII art splash or menu on first launch.

**Phase:** CLI server-launch integration.

---

## Minor Pitfalls

---

### Pitfall 12: `result_count` Always Returns 0 on Dashboard

**What goes wrong:** `SavedSearch.result_count` is always 0 (model field with no backing column). A dashboard "Recent Searches" component that displays result counts will always show "0 results" for every saved search, making the feature look broken.

**Prevention:** Remove the field from the model entirely (safest for the redesign), or add the database column and populate it during search runs. Do not wire up a UI widget that reads this field without fixing the underlying model.

**Phase:** Web dashboard redesign — check before building the saved searches overview component.

---

### Pitfall 13: InquirerPy "Zero Typing" Constraint Conflicts With Free-Text Fields

**What goes wrong:** The project requirement is "zero typing" — all navigation via arrows and Enter. However, the existing search model includes fields like `location` (city/ZIP text) that have no natural enumerated option list. Attempting to make everything arrow-key navigable forces either: (a) a dropdown of hard-coded metro areas (not flexible), or (b) a text input prompt (violates the zero-typing goal).

**Prevention:**
- Define the scope explicitly before implementation: "zero typing" applies to criteria fields with enumerated values (price range, beds, baths, sqft, etc.). Location entry uses a text prompt with autocomplete from previously used locations.
- InquirerPy's `FuzzyPrompt` provides a type-to-filter autocomplete that preserves the keyboard-first feel while allowing location entry — use it for the location field.
- Do not attempt to create dropdown lists of ZIP codes or cities; this creates a UX worse than typing.

**Phase:** Search wizard implementation.

---

### Pitfall 14: Deduplication Across CLI and Web Shows Different Result Counts

**What goes wrong:** Address-based deduplication is fragile (documented in CONCERNS.md). If the web UI redesign displays result counts prominently (e.g., "47 homes found") and those counts differ between the CLI and web results for the same search — because one path deduplicates and another doesn't — users will distrust the tool.

**Prevention:**
- Deduplication must happen in the service layer, not in the frontend or CLI display layer.
- Fix the `(source, source_id)` primary dedup key before the redesign makes result counts visible.
- Do not add result count badges to the UI until dedup correctness is validated.

**Phase:** Web UI redesign — do not build result count displays until dedup is fixed.

---

### Pitfall 15: Scheduler Thread Outlives CLI Process on Ctrl+C

**What goes wrong:** CONCERNS.md documents that `stop_scheduler()` is never called and the APScheduler background thread has no shutdown hook. If the CLI starts the FastAPI server and the user hits Ctrl+C, the server process may exit but the APScheduler thread continues running in a zombie state until the OS cleans it up.

**Prevention:**
- Register the `stop_scheduler` shutdown on the FastAPI `lifespan` (part of the `@app.on_event` migration fix).
- When the CLI launches the server as a subprocess, use `signal.SIGTERM` to shut it down cleanly on CLI exit.

**Phase:** Server launcher integration in the CLI.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| ASCII art splash | Art width overflow on narrow terminals | Check `os.get_terminal_size()` before rendering; have a fallback |
| Interactive menus | Rich + InquirerPy output conflict | Never run Live context concurrently with InquirerPy prompts |
| Search wizard | Blocking HTTP during arrow-key flow | Background thread + Rich spinner; escape key to cancel |
| SMTP wizard | Credential overwrite in .env | Use `python-dotenv` `set_key()`, not full-file write |
| Web UI redesign | Double `/api` prefix 404 on preview search | Fix route prefix bug before writing any new frontend code |
| Web UI redesign | Tailwind version mismatch on fresh install | Pin Tailwind version before styling work begins |
| Web dashboard | result_count always 0 | Remove or fix model field before building count displays |
| Global CLI command | Breaks after Homebrew Python update | Use pipx for global install, document in README |
| macOS .app | Gatekeeper rejection, ARM64 failures | Ship shell script launcher first; defer full .app bundle |
| Provider scraping | Silent 403 block with zero results | Add ProviderBlockedError distinction and user-facing message |
| FastAPI subprocess | Deprecation warnings corrupt Rich output | Fix lifespan migration; redirect subprocess stdout |

---

## Sources

- [InquirerPy GitHub Issues](https://github.com/kazhala/InquirerPy/issues) — known prompt_toolkit interactions (LOW confidence, GitHub issues browsed)
- [Rich Live Display docs](https://rich.readthedocs.io/en/latest/live.html) — Live context threading and overflow behavior (HIGH confidence, official docs)
- [Rich Issue #979 — track() inside Live()](https://github.com/willmcgugan/rich/issues/979) — component incompatibility (MEDIUM confidence, GitHub issue)
- [Rich Issue #1530 — thread safety](https://github.com/Textualize/rich/issues/1530) — Live + console threading (MEDIUM confidence, GitHub issue)
- [Rich Discussion #1791 — input during Live](https://github.com/Textualize/rich/discussions/1791) — prompting during Live context (MEDIUM confidence, GitHub discussion)
- [py2app FAQ](https://py2app.readthedocs.io/en/latest/faq.html) — dependency and framework issues (HIGH confidence, official docs)
- [PyInstaller Gatekeeper notarization thread](https://developer.apple.com/forums/thread/695989) — notarized app failures (MEDIUM confidence, Apple Developer Forums)
- [pipx documentation](https://github.com/pypa/pipx) — global Python CLI install best practice (HIGH confidence, official project)
- [pipx PATH issue on macOS](https://github.com/pipxproject/pipx/issues/461) — PATH resolution failure (MEDIUM confidence, GitHub issue)
- [Tailwind v4 dark mode migration](https://github.com/tailwindlabs/tailwindcss/discussions/16517) — config format changes breaking dark mode (MEDIUM confidence, official GitHub discussion)
- [HomeHarvest PyPI / GitHub](https://github.com/ZacharyHampton/HomeHarvest) — 403 blocking behavior (HIGH confidence, official README)
- [Redfin Scraping via ScrapeOps](https://scrapeops.io/websites/redfin/) — anti-scraping measures (MEDIUM confidence, community source)
- [FastAPI CORS docs](https://fastapi.tiangolo.com/tutorial/cors/) — wildcard origin and credential behavior (HIGH confidence, official docs)
- Internal CONCERNS.md — existing codebase issues used directly (HIGH confidence, first-party analysis)
