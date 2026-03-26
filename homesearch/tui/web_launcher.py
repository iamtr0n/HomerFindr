"""Background web server manager for the HomerFindr TUI.

Provides start/stop/is_running/get_port functions that launch FastAPI in a
daemon background thread, probe for a free port, and register an atexit hook
for graceful shutdown (PKG-02, PKG-04, PKG-05).
"""

import atexit
import socket
import threading
import time
from socket import AF_INET, SOCK_STREAM

import uvicorn

# Module-level singleton state
_server: "BackgroundServer | None" = None
_thread: "threading.Thread | None" = None
_current_port: "int | None" = None


class BackgroundServer(uvicorn.Server):
    """uvicorn.Server subclass that runs in a background daemon thread.

    Polls server.started after thread launch so callers can safely open a
    browser only after the server is ready to accept connections.
    """

    def run_in_thread(self) -> threading.Thread:
        """Start the server in a daemon thread and wait until it is ready.

        Returns:
            The started thread.
        """
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        # Poll until server signals startup is complete
        while not self.started:
            time.sleep(0.05)
        return t


def _find_free_port(start: int = 8000, end: int = 8010) -> int:
    """Return the first port in [start, end] that is free to bind.

    Uses socket.bind() (not connect()) to test whether the port is available
    from the server side. Walks start → end inclusive.

    Args:
        start: First port to probe (inclusive).
        end:   Last port to probe (inclusive).

    Returns:
        An available port number.

    Raises:
        RuntimeError: If no port in the range is available.
    """
    for port in range(start, end + 1):
        with socket.socket(AF_INET, SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}-{end}")


def start_server(host: str, port: int) -> int:
    """Start the FastAPI server in a background thread.

    If the server is already running, returns the current port immediately
    without starting a second instance.

    Args:
        host: Host address to bind (e.g. "127.0.0.1").
        port: Preferred port; probed first, falls back to next free port.

    Returns:
        The actual port the server bound to.

    Raises:
        RuntimeError: If no port in 8000-8010 is available.
    """
    global _server, _thread, _current_port

    if _server is not None and _server.started:
        return _current_port  # type: ignore[return-value]

    actual_port = _find_free_port(port)
    config = uvicorn.Config(
        "homesearch.api.routes:app",
        host=host,
        port=actual_port,
        log_level="error",
    )
    _server = BackgroundServer(config=config)
    _thread = _server.run_in_thread()
    atexit.register(stop_server)  # PKG-04: safety net for abrupt exits
    _current_port = actual_port
    return actual_port


def stop_server() -> None:
    """Signal graceful shutdown and join the server thread.

    Safe to call when no server is running (no-op in that case).
    Resets module-level globals after shutdown.
    """
    global _server, _thread, _current_port

    if _server is not None:
        _server.should_exit = True
        if _thread is not None:
            _thread.join(timeout=5)
    _server = None
    _thread = None
    _current_port = None


def is_running() -> bool:
    """Return True if the background server is started and accepting connections."""
    return _server is not None and _server.started


def get_port() -> "int | None":
    """Return the port the server is currently bound to, or None if not running."""
    return _current_port
