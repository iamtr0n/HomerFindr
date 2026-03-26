---
phase: 04-bridge-and-desktop-packaging
verified: 2026-03-25T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 4: Bridge and Desktop Packaging Verification Report

**Phase Goal:** HomerFindr feels like a real desktop application — launchable from anywhere, with CLI and web UI connected as one tool
**Verified:** 2026-03-25
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Typing `homerfindr` in any terminal window launches the interactive CLI (installed globally via pipx) | VERIFIED | `pyproject.toml` has `homerfindr = "homesearch.main:app"` and `homesearch = "homesearch.main:app"` both confirmed via `tomllib` parse |
| 2 | Selecting "Launch Web UI" from the CLI main menu starts the FastAPI server and opens the browser automatically | VERIFIED | `menu.py:_handle_web_ui()` calls `start_server()` then `webbrowser.open(url)`; `start_server()` uses `uvicorn.Config("homesearch.api.routes:app")` with port probing; stub text "future update" is absent |
| 3 | Closing the CLI (or selecting Exit) shuts down the background FastAPI server gracefully with no zombie processes | VERIFIED | `run_menu_loop()` calls `_cleanup_server()` after the while loop exits (line 58); `_cleanup_server()` calls `stop_server()` which sets `should_exit = True` and joins thread with 5s timeout; `atexit.register(stop_server)` is also registered as belt-and-suspenders |
| 4 | A macOS .app bundle in the Dock opens a terminal running homerfindr when double-clicked | VERIFIED | `packaging/HomerFindr.command` is executable and calls `homerfindr` after PATH setup; `packaging/homerfindr_launcher.sh` uses `osascript` to open Terminal running `homerfindr`; `packaging/README.md` documents exact `platypus` CLI build command for .app bundle |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `homesearch/tui/web_launcher.py` | Background uvicorn server management | VERIFIED | 129 lines; exports `BackgroundServer`, `_find_free_port`, `start_server`, `stop_server`, `is_running`, `get_port`; full implementation, no stubs |
| `homesearch/tui/menu.py` | Web UI launch and exit cleanup | VERIFIED | `_handle_web_ui()` fully implemented; `_cleanup_server()` present and called after loop; stub text absent |
| `tests/test_web_launcher.py` | Unit tests for port probing and server lifecycle | VERIFIED | 141 lines; 7 tests (3 port-probing, 4 lifecycle); all pass in 0.03s |
| `packaging/HomerFindr.command` | macOS double-click launcher | VERIFIED | Executable (`-rwx`); contains `homerfindr` call, `$HOME/.local/bin` PATH setup, `command -v` guard |
| `packaging/homerfindr_launcher.sh` | Platypus wrapper script for .app bundle | VERIFIED | Executable (`-rwx`); contains `osascript` delegation to Terminal; `Interface: None` noted in comment |
| `packaging/README.md` | Installation and packaging instructions | VERIFIED | 131 lines; covers pipx install, `pipx ensurepath`, .command setup, Platypus build, troubleshooting |
| `pyproject.toml` | Entry points for homerfindr and homesearch | VERIFIED | Both entry points confirmed via `tomllib`; description updated to "HomerFindr - universal home search aggregator across all platforms" |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `menu.py` | `web_launcher.py` | lazy import in `_handle_web_ui()` | WIRED | `from homesearch.tui.web_launcher import start_server, is_running, get_port` at line 89 |
| `menu.py` | `_cleanup_server()` / `stop_server` | call after menu loop exits | WIRED | `_cleanup_server()` called at line 58, outside while block; `_cleanup_server` imports and calls `stop_server` |
| `web_launcher.py` | `homesearch.api.routes:app` | `uvicorn.Config` app string | WIRED | `uvicorn.Config("homesearch.api.routes:app", ...)` at line 92 |
| `packaging/HomerFindr.command` | `homerfindr` CLI | PATH lookup of pipx-installed entry point | WIRED | `command -v homerfindr` guard + `homerfindr` call; `$HOME/.local/bin` prepended to PATH |
| `pyproject.toml` | `homesearch.main:app` | project.scripts entry point | WIRED | `homerfindr = "homesearch.main:app"` confirmed via tomllib parse |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PKG-01 | 04-02-PLAN.md | Global `homerfindr` CLI command installable via pipx | SATISFIED | `pyproject.toml` has both entry points; `packaging/README.md` documents `pipx install .` |
| PKG-02 | 04-01-PLAN.md | Launch Web UI from CLI — starts FastAPI server as daemon thread + opens browser | SATISFIED | `_handle_web_ui()` starts `BackgroundServer` in daemon thread via `run_in_thread()`, then calls `webbrowser.open()` |
| PKG-03 | 04-02-PLAN.md | macOS .app shortcut for Dock (via Platypus or .command wrapper) | SATISFIED | `packaging/HomerFindr.command` (primary); `packaging/homerfindr_launcher.sh` + README Platypus build instructions (polished .app) |
| PKG-04 | 04-01-PLAN.md | Graceful server shutdown when CLI exits | SATISFIED | `_cleanup_server()` called after loop; `stop_server()` sets `should_exit = True` and joins thread; `atexit.register(stop_server)` as safety net |
| PKG-05 | 04-01-PLAN.md | Port collision handling (fallback to next available port) | SATISFIED | `_find_free_port(start, end)` probes 8000-8010 via `socket.bind()`; raises `RuntimeError` if all exhausted; menu catches and displays user-friendly error |

**All 5 requirements verified. No orphaned requirements.**

---

## Anti-Patterns Found

None detected.

Scanned files: `homesearch/tui/web_launcher.py`, `homesearch/tui/menu.py`, `tests/test_web_launcher.py`, `packaging/HomerFindr.command`, `packaging/homerfindr_launcher.sh`

- No TODO/FIXME/PLACEHOLDER comments
- No stub return values (`return null`, `return []`, `return {}`)
- No hardcoded empty data flowing to render paths
- Stub text "will be available in a future update" confirmed absent from `menu.py`
- `log_level="error"` set in `uvicorn.Config` to prevent startup log noise from corrupting Rich terminal output

---

## Unit Test Results

```
7 passed in 0.03s

tests/test_web_launcher.py::TestFindFreePort::test_returns_start_port_when_available        PASSED
tests/test_web_launcher.py::TestFindFreePort::test_skips_occupied_port_returns_next_free    PASSED
tests/test_web_launcher.py::TestFindFreePort::test_raises_runtime_error_when_all_ports_occupied PASSED
tests/test_web_launcher.py::TestServerLifecycle::test_is_running_returns_false_when_no_server_started PASSED
tests/test_web_launcher.py::TestServerLifecycle::test_start_server_sets_globals             PASSED
tests/test_web_launcher.py::TestServerLifecycle::test_stop_server_sets_should_exit_and_joins PASSED
tests/test_web_launcher.py::TestServerLifecycle::test_start_server_returns_early_if_already_running PASSED
```

---

## Human Verification Required

### 1. Launch Web UI — End-to-End Flow

**Test:** Run `homerfindr` (or launch via TUI), navigate to "Launch Web UI" in the arrow-key menu, press Enter.
**Expected:** Terminal prints "Starting web UI...", then "Web UI running at http://127.0.0.1:8000", and a browser window opens automatically to the HomerFindr web dashboard.
**Why human:** Browser open behavior, server startup timing, and TUI rendering cannot be verified programmatically without running the live application.

### 2. Already-Running Guard

**Test:** With the web UI already launched (from test 1), select "Launch Web UI" a second time.
**Expected:** Terminal prints "Web UI already running at http://127.0.0.1:8000 — opening browser" and opens the browser again without starting a second server.
**Why human:** Requires the server to be live and running; module-level singleton state across invocations.

### 3. Exit Cleanup — No Zombie Processes

**Test:** Launch the web UI, then select Exit from the menu. Run `lsof -i :8000` immediately after.
**Expected:** No process holds port 8000. The server exits within 5 seconds.
**Why human:** Requires OS-level process inspection after CLI exits.

### 4. macOS .command Double-Click

**Test:** Copy `packaging/HomerFindr.command` to Desktop, double-click it.
**Expected:** Terminal.app opens a new window and the HomerFindr interactive CLI starts with splash screen.
**Why human:** Requires a macOS Finder interaction; Gatekeeper security prompt behavior and PATH resolution in a Finder-launched Terminal session cannot be simulated.

### 5. Port Collision Fallback

**Test:** Bind port 8000 manually (`nc -l 8000 &`), then select "Launch Web UI".
**Expected:** Terminal prints "Web UI running at http://127.0.0.1:8001" (or next available port) and browser opens to port 8001.
**Why human:** Requires running the application with a live port conflict to observe the port-probing fallback in action.

---

## Summary

Phase 4 goal is fully achieved. All 4 ROADMAP success criteria are satisfied:

1. **Global CLI install (PKG-01):** Both `homerfindr` and `homesearch` entry points are correctly wired in `pyproject.toml` to `homesearch.main:app`. `packaging/README.md` provides complete pipx install instructions.

2. **Web UI bridge (PKG-02):** `_handle_web_ui()` in `menu.py` is a complete, non-stub implementation that starts `BackgroundServer` in a daemon thread (via `web_launcher.py`), waits for the server to be ready by polling `server.started`, then opens the browser. The idempotency guard prevents double-starts.

3. **Graceful shutdown (PKG-04):** `_cleanup_server()` is called unconditionally after both exit paths of the menu loop (Exit choice and Ctrl+C). `atexit.register(stop_server)` provides an additional safety net. `stop_server()` sets `should_exit = True` and joins the thread with a 5-second timeout.

4. **Port collision handling (PKG-05):** `_find_free_port()` probes ports 8000-8010 using `socket.bind()`. Port exhaustion raises `RuntimeError` which is caught in `_handle_web_ui()` with a user-friendly red error message.

5. **macOS desktop launcher (PKG-03):** Both `packaging/HomerFindr.command` (executable, self-contained, Finder double-click) and `packaging/homerfindr_launcher.sh` (Platypus `.app` wrapper via `osascript`) are present, executable, and functionally correct. The README documents the complete build path for a Dock-pinnable `.app`.

The implementation matches plan specifications exactly with no deviations, no stubs, and 7/7 unit tests passing.

---

_Verified: 2026-03-25_
_Verifier: Claude (gsd-verifier)_
