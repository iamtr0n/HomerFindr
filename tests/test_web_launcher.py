"""Unit tests for homesearch.tui.web_launcher — port probing and server lifecycle."""

import threading
import unittest
from unittest.mock import MagicMock, patch

import pytest


class TestFindFreePort:
    """Tests for _find_free_port port probing logic."""

    def test_returns_start_port_when_available(self):
        """Test 1: _find_free_port returns the first port when it is available."""
        from homesearch.tui.web_launcher import _find_free_port

        mock_socket = MagicMock()
        mock_socket.__enter__ = MagicMock(return_value=mock_socket)
        mock_socket.__exit__ = MagicMock(return_value=False)
        mock_socket.bind = MagicMock()  # No exception = port is free

        with patch("homesearch.tui.web_launcher.socket.socket", return_value=mock_socket):
            result = _find_free_port(8000, 8010)

        assert result == 8000
        mock_socket.bind.assert_called_once_with(("127.0.0.1", 8000))

    def test_skips_occupied_port_returns_next_free(self):
        """Test 2: _find_free_port skips occupied ports and returns the next free one."""
        from homesearch.tui.web_launcher import _find_free_port

        call_count = 0

        def bind_side_effect(addr):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("Address already in use")
            # Second call succeeds

        mock_socket = MagicMock()
        mock_socket.__enter__ = MagicMock(return_value=mock_socket)
        mock_socket.__exit__ = MagicMock(return_value=False)
        mock_socket.bind = MagicMock(side_effect=bind_side_effect)

        with patch("homesearch.tui.web_launcher.socket.socket", return_value=mock_socket):
            result = _find_free_port(8000, 8010)

        assert result == 8001
        assert mock_socket.bind.call_count == 2

    def test_raises_runtime_error_when_all_ports_occupied(self):
        """Test 3: _find_free_port raises RuntimeError when all ports in range are occupied."""
        from homesearch.tui.web_launcher import _find_free_port

        mock_socket = MagicMock()
        mock_socket.__enter__ = MagicMock(return_value=mock_socket)
        mock_socket.__exit__ = MagicMock(return_value=False)
        mock_socket.bind = MagicMock(side_effect=OSError("Address already in use"))

        with patch("homesearch.tui.web_launcher.socket.socket", return_value=mock_socket):
            with pytest.raises(RuntimeError, match="No free port found in range"):
                _find_free_port(8000, 8001)


class TestServerLifecycle:
    """Tests for server state management functions."""

    def setup_method(self):
        """Reset module-level globals before each test."""
        import homesearch.tui.web_launcher as wl
        wl._server = None
        wl._thread = None
        wl._current_port = None

    def test_is_running_returns_false_when_no_server_started(self):
        """Test 4: is_running() returns False when no server has been started."""
        from homesearch.tui.web_launcher import is_running

        assert is_running() is False

    def test_start_server_sets_globals(self):
        """Test 5: start_server sets module-level _server and _thread globals."""
        import homesearch.tui.web_launcher as wl
        from homesearch.tui.web_launcher import start_server

        mock_server = MagicMock()
        mock_server.started = True
        mock_thread = MagicMock()

        with patch("homesearch.tui.web_launcher._find_free_port", return_value=8000), \
             patch("homesearch.tui.web_launcher.uvicorn.Config"), \
             patch("homesearch.tui.web_launcher.BackgroundServer", return_value=mock_server), \
             patch.object(mock_server, "run_in_thread", return_value=mock_thread), \
             patch("homesearch.tui.web_launcher.atexit.register"):

            actual_port = start_server("127.0.0.1", 8000)

        assert wl._server is mock_server
        assert wl._thread is mock_thread
        assert wl._current_port == 8000
        assert actual_port == 8000

    def test_stop_server_sets_should_exit_and_joins(self):
        """Test 6: stop_server sets server.should_exit = True and calls thread.join."""
        import homesearch.tui.web_launcher as wl
        from homesearch.tui.web_launcher import stop_server

        mock_server = MagicMock()
        mock_server.started = True
        mock_thread = MagicMock()

        wl._server = mock_server
        wl._thread = mock_thread
        wl._current_port = 8000

        stop_server()

        assert mock_server.should_exit is True
        mock_thread.join.assert_called_once_with(timeout=5)
        assert wl._server is None
        assert wl._thread is None
        assert wl._current_port is None

    def test_start_server_returns_early_if_already_running(self):
        """Test 7: start_server returns early (same port) if server is already running."""
        import homesearch.tui.web_launcher as wl
        from homesearch.tui.web_launcher import start_server

        mock_server = MagicMock()
        mock_server.started = True

        wl._server = mock_server
        wl._current_port = 8000

        with patch("homesearch.tui.web_launcher._find_free_port") as mock_find_port:
            result = start_server("127.0.0.1", 8000)

        mock_find_port.assert_not_called()
        assert result == 8000
