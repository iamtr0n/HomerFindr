# Phase 4: Bridge and Desktop Packaging - Research

**Researched:** 2026-03-25
**Domain:** Python packaging (pipx), uvicorn programmatic API, macOS .app bundling (Platypus / .command)
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PKG-01 | Global `homerfindr` CLI command installable via pipx | Entry point already in pyproject.toml; `pipx install .` is the install path |
| PKG-02 | Launch Web UI from CLI — starts FastAPI server as daemon thread + opens browser | `uvicorn.Server` + `threading.Thread` + `webbrowser.open()` pattern verified |
| PKG-03 | macOS .app shortcut for Dock (via Platypus or .command wrapper) | Both approaches documented; .command is zero-dependency fallback; Platypus is polished option |
| PKG-04 | Graceful server shutdown when CLI exits | `server.should_exit = True` + `thread.join()` pattern; atexit registration for safety |
| PKG-05 | Port collision handling (fallback to next available port) | `socket.bind()` probe pattern works; scan 8000–8010 range |
</phase_requirements>

---

## Summary

Phase 4 has two independent technical tracks: (1) wiring the background web server into the CLI menu stub already in place, and (2) providing a macOS launch shortcut. The CLI track uses a well-established pattern — subclassing `uvicorn.Server` and running it in a `daemon=True` background thread with `server.should_exit = True` for graceful shutdown. The macOS track has two valid options: a `.command` shell script (zero-dependency, works today) or a Platypus-generated `.app` (polished Dock experience, requires Platypus to be installed by the developer once). The project already has `homerfindr` wired as an entry point in `pyproject.toml`, so PKG-01 requires only documentation and validation, not new code.

The biggest risk is zombie processes if the CLI exits without joining the server thread. The `atexit` module and explicit `server.should_exit = True` both need to be used; relying on `daemon=True` alone is insufficient for clean shutdown because daemon threads are killed abruptly at interpreter exit, which can corrupt SQLite state.

**Primary recommendation:** Implement background uvicorn via `Server` subclass + `threading.Thread`. For PKG-03 use a `.command` file as the primary deliverable (works on any Mac, no tooling), and optionally provide Platypus build instructions as a developer note.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uvicorn | 0.42.0 (installed) | ASGI server; runs FastAPI | Already in project |
| threading | stdlib | Background thread for server | No extra install |
| socket | stdlib | Port availability probe | No extra install |
| webbrowser | stdlib | Open browser to local URL | No extra install |
| atexit | stdlib | Register shutdown hook on interpreter exit | No extra install |
| pipx | latest (user-installed) | Install Python CLI tools globally | Standard tool for CLI apps |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Platypus CLI | 5.5.0 | Build macOS .app from shell script | When developer wants polished Dock icon |
| `.command` file | n/a (shell) | Double-click Terminal launcher, no tooling | Simplest macOS shortcut option |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uvicorn.Server subclass | subprocess.Popen uvicorn | Subprocess is harder to shut down cleanly; also duplicates PATH requirements |
| uvicorn.Server subclass | multiprocessing.Process | More isolation but requires pickling the FastAPI app object; overkill here |
| Platypus .app | PyInstaller | PyInstaller bundles Python runtime (100–200 MB); massive overkill for a local tool |
| Platypus .app | Automator .app | Automator is fragile across macOS versions and hard to script |
| .command file | AppleScript .app | AppleScript `.app` bundles need Xcode/Script Editor; .command is simpler |

**Installation (for global CLI):**
```bash
# Production install
pipx install .

# Development install (changes to source reflected immediately except entry point changes)
pipx install --editable .

# Verify
homerfindr --help
```

---

## Architecture Patterns

### Recommended Project Structure

New code is contained in two places:

```
homesearch/
├── tui/
│   ├── menu.py           # _handle_web_ui() stub — replace with real launcher
│   └── web_launcher.py   # NEW: background server manager (PKG-02, PKG-04, PKG-05)
packaging/
│   └── HomerFindr.command  # NEW: macOS double-click launcher (PKG-03)
```

No new top-level packages. `web_launcher.py` is a new module in `homesearch/tui/` keeping all TUI concerns together.

### Pattern 1: Background uvicorn Server

**What:** Subclass `uvicorn.Server` to expose a `run_in_background()` context manager. Store the server instance as a module-level singleton so menu.py can call `stop_server()` at exit.

**When to use:** Any time the CLI needs to start/stop the web server without blocking the menu loop.

**How it works:**
- `uvicorn.Server` has a `should_exit: bool` attribute (verified against uvicorn 0.42.0 source)
- Setting `should_exit = True` from another thread causes the server's async loop to exit gracefully
- Poll `server.started` after thread start to confirm readiness before opening the browser
- `thread.daemon = True` ensures the thread doesn't block interpreter exit if the user force-quits

```python
# Source: https://bugfactory.io/articles/starting-and-stopping-uvicorn-in-the-background/
# Pattern adapted for HomerFindr — module-level singleton

import threading
import time
import webbrowser
import atexit
import uvicorn

_server: "BackgroundServer | None" = None
_thread: "threading.Thread | None" = None


class BackgroundServer(uvicorn.Server):
    """uvicorn.Server subclass that can run in a background thread."""

    def run_in_thread(self) -> threading.Thread:
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        # Wait for server to signal startup complete
        while not self.started:
            time.sleep(0.05)
        return t


def start_server(host: str, port: int) -> int:
    """Start FastAPI in a background thread. Returns actual port used."""
    global _server, _thread
    if _server is not None and _server.started:
        return port  # Already running

    port = _find_free_port(port)
    config = uvicorn.Config(
        "homesearch.api.routes:app",
        host=host,
        port=port,
        log_level="error",   # suppress startup noise from Rich terminal
    )
    _server = BackgroundServer(config=config)
    _thread = _server.run_in_thread()
    atexit.register(stop_server)   # PKG-04: safety net
    return port


def stop_server() -> None:
    """Signal graceful shutdown and join the server thread."""
    global _server, _thread
    if _server is not None:
        _server.should_exit = True
        if _thread is not None:
            _thread.join(timeout=5)
        _server = None
        _thread = None
```

### Pattern 2: Port Collision Probe (PKG-05)

**What:** Before starting uvicorn, probe candidate ports with `socket.bind()`. Walk 8000 → 8010.

**When to use:** Always call before `uvicorn.Config(port=...)`.

```python
import socket

def _find_free_port(start: int = 8000, end: int = 8010) -> int:
    """Return the first free port in [start, end]. Raises RuntimeError if none free."""
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}–{end}")
```

**Verified:** `socket.bind()` on `127.0.0.1:8000` returned `OSError` when port was in use (confirmed locally against running server). Pattern is idiomatic Python.

### Pattern 3: _handle_web_ui() Integration

**What:** Replace the stub in `menu.py` with calls to `web_launcher.py`.

```python
def _handle_web_ui():
    """Start background FastAPI server and open browser."""
    from homesearch.tui.web_launcher import start_server, stop_server, is_running
    from homesearch.tui.styles import console
    from homesearch.config import settings
    import webbrowser

    if is_running():
        url = f"http://{settings.host}:{_current_port()}"
        console.print(f"[green]Web UI already running — opening {url}[/green]")
        webbrowser.open(url)
        return

    console.print("[dim]Starting web UI...[/dim]")
    port = start_server(settings.host, settings.port)
    url = f"http://{settings.host}:{port}"
    console.print(f"[bold green]Web UI running at {url}[/bold green]")
    webbrowser.open(url)
```

**Exit cleanup:** `run_menu_loop()` already breaks on Exit/Ctrl+C — add `stop_server()` call after the `while True` loop exits.

### Pattern 4: macOS .command Launcher (PKG-03)

**What:** A shell script with `.command` extension that Terminal.app opens when double-clicked. File must be `chmod +x`.

**When to use:** Primary PKG-03 deliverable — zero tooling dependencies.

```bash
#!/bin/bash
# packaging/HomerFindr.command
# Double-click this file to launch HomerFindr CLI in a Terminal window.

# Source user shell profile to get pipx PATH
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" 2>/dev/null
[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc" 2>/dev/null

# Try pipx bin path directly as fallback
export PATH="$HOME/.local/bin:$PATH"

if command -v homerfindr &>/dev/null; then
    homerfindr
else
    echo "HomerFindr not found. Install with: pipx install /path/to/HomerFindr"
    echo "Press Enter to close."
    read
fi
```

**Key behavior:** macOS Terminal.app opens a new window, runs the script, leaves the window open if the script exits with a non-zero code or if "Close window on exit of process" is NOT set in Terminal preferences. The `.command` extension is the macOS-recognized convention for "open in Terminal."

### Pattern 5: Platypus .app Bundle (PKG-03 polished option)

**What:** Platypus 5.5.0 wraps a shell script in a native macOS `.app` bundle. The `.app` can live in `/Applications` and be pinned to the Dock.

**Limitation discovered:** Platypus's interface types (Progress Bar, Text Window, None) do NOT provide an interactive terminal. The `stdin` FAQ explicitly states: "Platypus apps cannot prompt for input via stdin" — which means the questionary arrow-key TUI **will not work** inside a Platypus Text Window app.

**Correct Platypus approach for HomerFindr:** Use `Interface: None` + `open -a Terminal` in the wrapped script to launch a real Terminal.app session running `homerfindr`. The Platypus app acts as a Dock launcher only — it immediately hands off to Terminal.

```bash
#!/bin/bash
# Script wrapped by Platypus with Interface: None
# This script is what Platypus executes when the .app is launched

# Ensure pipx bin is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Open a new Terminal window running homerfindr
osascript -e 'tell application "Terminal" to do script "export PATH=\"$HOME/.local/bin:$PATH\"; homerfindr"'
```

**Platypus CLI invocation (once Platypus.app is installed and CLI tool enabled):**
```bash
/usr/local/bin/platypus \
  --name "HomerFindr" \
  --interface-type None \
  --author "HomerFindr" \
  --bundle-identifier "com.homerfindr.app" \
  --overwrite \
  packaging/homerfindr_launcher.sh \
  packaging/HomerFindr.app
```

**Installation after build:**
```bash
cp -r packaging/HomerFindr.app /Applications/
```

### Anti-Patterns to Avoid

- **Calling `uvicorn.run()` directly in the menu thread:** `uvicorn.run()` is a blocking call — it takes over the event loop and the CLI menu freezes. Always use `uvicorn.Server` + a background thread.
- **`daemon=True` as the only shutdown mechanism:** Daemon threads are killed abruptly at interpreter exit. SQLite connections mid-write can be left in an inconsistent state. Always call `server.should_exit = True` + `thread.join()` before exit.
- **Platypus Text Window interface:** questionary and Rich both need an interactive terminal with `stdin` — Platypus's output-only Text Window breaks both. Use `Interface: None` + osascript to open Terminal instead.
- **Opening the browser before the server is ready:** `webbrowser.open()` before `server.started == True` results in a 502/connection refused in the browser. Always poll `started` first.
- **Port probing with `socket.connect()` instead of `socket.bind()`:** `connect()` tests if something IS listening (wrong direction); `bind()` tests if the port IS FREE (correct direction).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Running ASGI app in background | Custom subprocess launch | `uvicorn.Server` + thread | Server manages its own async loop; subprocess adds PATH/env complexity |
| Port availability check | Regex parsing of `netstat` output | `socket.bind()` probe | `netstat` output varies by OS; `socket` is stdlib and cross-platform |
| Browser launch | `subprocess.Popen(['open', url])` | `webbrowser.open(url)` | `webbrowser` is cross-platform stdlib; `open` is macOS-only |
| macOS app bundle structure | Manual `Info.plist` + binary creation | Platypus CLI or `.command` | `.app` bundle format has Apple-specific requirements; wrong structure = quarantine errors |

**Key insight:** The background server problem looks simple but has subtle edge cases — signal handling, event loop ownership, thread-safe shutdown. `uvicorn.Server` already handles all of these; the subclass adds only the `started` polling needed by the caller.

---

## Common Pitfalls

### Pitfall 1: uvicorn log output corrupts Rich terminal
**What goes wrong:** uvicorn's default log config writes INFO lines to stdout/stderr while Rich has terminal ownership. This produces garbled output in the CLI.
**Why it happens:** uvicorn uses Python's `logging` module; Rich's Console and Live don't intercept it.
**How to avoid:** Pass `log_level="error"` to `uvicorn.Config` — suppresses startup and access log chatter. Only errors surface.
**Warning signs:** Seeing `INFO: Application startup complete` interspersed with menu output.

### Pitfall 2: pipx doesn't find `homerfindr` after install
**What goes wrong:** `homerfindr: command not found` even after `pipx install .`
**Why it happens:** `~/.local/bin` is not in `$PATH` on some macOS setups (especially if pipx was just installed).
**How to avoid:** After `pipx install`, run `pipx ensurepath` and restart the terminal. Document this in the install instructions.
**Warning signs:** `which homerfindr` returns nothing; `~/.local/bin/homerfindr` exists.

### Pitfall 3: Server still running after CLI exit (zombie)
**What goes wrong:** After the user selects Exit, the web server keeps listening on port 8000 indefinitely.
**Why it happens:** `daemon=True` alone means the thread dies only when the main thread dies — but if the Python process stays alive for any reason (atexit handler delays, etc.) the server keeps running.
**How to avoid:** Explicitly call `stop_server()` in the `run_menu_loop()` exit path AND register with `atexit.register(stop_server)` as a safety net.
**Warning signs:** Running `lsof -i :8000` after CLI exit shows uvicorn still bound to the port.

### Pitfall 4: Platypus stdin limitation breaks TUI
**What goes wrong:** Wrapping `homerfindr` directly as the Platypus script causes questionary to fail — no interactive stdin.
**Why it happens:** Platypus captures stdout only; stdin is never connected to user input.
**How to avoid:** Platypus script must use `osascript` to delegate to a real Terminal.app session. The `.app` is a launcher, not a host.
**Warning signs:** questionary raises `KeyboardInterrupt` or displays nothing on selection attempts.

### Pitfall 5: Port probe race condition
**What goes wrong:** Port 8001 is free when probed, but taken by the time uvicorn tries to bind it.
**Why it happens:** Small TOCTOU window between `socket.bind()` probe and `uvicorn.Config(port=...)`.
**How to avoid:** Accept this as a low-probability edge case. Add a try/except around `start_server()` that increments the port and retries once if uvicorn raises `OSError` on bind.
**Warning signs:** `OSError: [Errno 48] Address already in use` in uvicorn startup.

### Pitfall 6: .command file PATH missing pipx bin
**What goes wrong:** Double-clicking `HomerFindr.command` opens Terminal but says `homerfindr: command not found`.
**Why it happens:** Terminal.app launched by Finder doesn't source the user's full shell profile; `.bashrc`/`.zshrc` sourcing is unreliable in this context.
**How to avoid:** Explicitly prepend `$HOME/.local/bin` to `PATH` at the top of the `.command` script as a hardcoded fallback, in addition to sourcing the profile.
**Warning signs:** `echo $PATH` in the Terminal window doesn't include `~/.local/bin`.

---

## Code Examples

Verified patterns from official sources:

### uvicorn.Server background thread (complete working pattern)
```python
# Source: https://bugfactory.io/articles/starting-and-stopping-uvicorn-in-the-background/
# Adapted: polled server.started attribute verified against uvicorn 0.42.0

import threading
import time
import uvicorn

class BackgroundServer(uvicorn.Server):
    def run_in_thread(self) -> threading.Thread:
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        while not self.started:
            time.sleep(0.05)
        return t

# Usage
config = uvicorn.Config("homesearch.api.routes:app", host="127.0.0.1", port=8000, log_level="error")
server = BackgroundServer(config)
thread = server.run_in_thread()
# ... later, to stop:
server.should_exit = True
thread.join(timeout=5)
```

### pipx install (entry point already in pyproject.toml)
```bash
# From project root — installs both `homesearch` and `homerfindr` entry points
pipx install .

# Verify both entry points are available
which homerfindr  # → ~/.local/bin/homerfindr
which homesearch  # → ~/.local/bin/homesearch

# If PATH is missing:
pipx ensurepath
```

### macOS .command launcher (minimal)
```bash
#!/bin/bash
# HomerFindr.command — make executable with: chmod +x HomerFindr.command
export PATH="$HOME/.local/bin:$PATH"
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc" 2>/dev/null
homerfindr
```

### Port probe
```python
import socket

def _find_free_port(start: int = 8000, end: int = 8010) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port in {start}–{end}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `uvicorn.run()` with `asyncio.run()` in thread | `uvicorn.Server` subclass + `server.should_exit` | uvicorn ~0.14+ | Clean programmatic shutdown without signal hacks |
| `on_event("startup")` / `on_event("shutdown")` | `asynccontextmanager` lifespan | FastAPI 0.93+ | Already migrated in Phase 1 of this project |

**Deprecated/outdated:**
- `loop.stop()` / signal-based uvicorn shutdown: These patterns predate `server.should_exit` and require event loop access from outside the thread — fragile.
- PyInstaller for "desktop packaging" of CLI tools: Creates enormous self-contained binaries (100–200 MB). pipx is the correct tool for Python CLI distribution.

---

## Open Questions

1. **Platypus availability assumption**
   - What we know: Platypus 5.5.0 is not installed on the current machine; the CLI tool (`/usr/local/bin/platypus`) is not present.
   - What's unclear: The project decision (from STATE.md) says "Use Platypus for macOS .app" — but Platypus must be installed by the developer before PKG-03 can produce a `.app`.
   - Recommendation: Make the `.command` file the automated deliverable (committed to repo, immediately usable). Provide Platypus build instructions as a separate developer note. The plan should not require Platypus to be installed in CI or on any specific machine.

2. **Server singleton lifecycle with multiple "Launch Web UI" invocations**
   - What we know: The menu loop can call `_handle_web_ui()` multiple times if the user returns to the menu.
   - What's unclear: Should re-invoking "Launch Web UI" start a new server (after the old one was closed from the browser) or just re-open the browser if already running?
   - Recommendation: Check `server.started` state. If running, re-open browser only. If not running (e.g., after explicit stop), restart. This covers the common case cleanly.

3. **`homesearch serve` command vs new background launcher**
   - What we know: `main.py` has a `serve` command that calls `uvicorn.run()` (blocking). The new `web_launcher.py` will use the non-blocking pattern.
   - What's unclear: Should `serve` be refactored to reuse `web_launcher.py`, or stay as a separate blocking path?
   - Recommendation: Keep `serve` as-is (it's a power-user path used directly from the terminal). `web_launcher.py` is CLI-menu-only. Avoid entangling them.

---

## Sources

### Primary (HIGH confidence)
- Platypus 5.5.0 Documentation (gh repo clone sveinbjornt/Platypus) — interface types, stdin limitation, CLI tool usage, osascript approach
- uvicorn 0.42.0 installed package — `Server` class methods (`should_exit`, `started`, `run`), `Config` signature verified via `inspect`
- Python stdlib (`threading`, `socket`, `webbrowser`, `atexit`) — available and verified via `uv run python3`
- `pyproject.toml` in project — `homerfindr` entry point already defined at `homesearch.main:app`
- `homesearch/tui/menu.py` — `_handle_web_ui()` stub confirmed at line 85–87

### Secondary (MEDIUM confidence)
- https://bugfactory.io/articles/starting-and-stopping-uvicorn-in-the-background/ — `BackgroundServer` subclass pattern, `server.started` polling; cross-referenced against uvicorn source
- https://pipx.pypa.io/latest/docs/ — `pipx install .` and `--editable` flag, `ensurepath` command
- WebSearch (multiple sources) — `.command` file macOS behavior; cross-verified against community reports from Apple developer forums

### Tertiary (LOW confidence)
- General WebSearch — Platypus Dock integration behavior for `Interface: None` + osascript pattern. The osascript approach is widely used but not in the official Platypus documentation directly; the documentation confirms stdin limitation which drives this approach.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified as installed or stdlib; entry points confirmed in pyproject.toml
- Architecture: HIGH — uvicorn.Server pattern verified against installed uvicorn 0.42.0; socket.bind() approach tested locally
- Pitfalls: HIGH for items 1–3 (verified against code); MEDIUM for items 4–6 (derived from docs + community reports)

**Research date:** 2026-03-25
**Valid until:** 2026-09-25 (stable APIs; pipx/uvicorn rarely break these patterns)
