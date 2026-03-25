"""Main menu loop — arrow-key navigation with questionary."""

import questionary

from homesearch.tui.styles import HOUSE_STYLE, console
from homesearch.tui.splash import show_splash


def tui_main():
    """Entry point for the interactive TUI experience.

    Shows splash, then loops the main menu until Exit or Ctrl+C.
    Per D-03: splash on every launch.
    Per D-06: first-run check triggers wizard when no config exists.
    Per D-07: return to menu after any action (while True loop).
    """
    show_splash()
    # First-run check — triggers when no config file exists (D-06)
    from homesearch.tui.config import config_exists
    from homesearch.tui.first_run import run_first_run_wizard
    if not config_exists():
        run_first_run_wizard()
    run_menu_loop()


def run_menu_loop():
    """Arrow-key main menu loop. Per D-06, options in this exact order."""
    while True:
        try:
            choice = questionary.select(
                "What would you like to do?",
                choices=[
                    "\U0001f3e0  New Search",
                    "\U0001f4cb  Saved Searches",
                    "\u2699\ufe0f   Settings",
                    "\U0001f310  Launch Web UI",
                    "\U0001f6aa  Exit",
                ],
                style=HOUSE_STYLE,
            ).ask()

            if choice is None or "Exit" in choice:
                console.print("[bold cyan]Goodbye! \U0001f3e0[/bold cyan]")
                break
            elif "New Search" in choice:
                _handle_new_search()
            elif "Saved Searches" in choice:
                _handle_saved_searches()
            elif "Settings" in choice:
                _handle_settings()
            elif "Launch Web UI" in choice:
                _handle_web_ui()

        except KeyboardInterrupt:
            console.print("\n[bold cyan]Goodbye! \U0001f3e0[/bold cyan]")
            break


def _handle_new_search():
    """Run the full search flow: wizard -> spinner -> results -> save."""
    from homesearch.tui.wizard import run_search_wizard
    from homesearch.tui.results import execute_search_with_spinner, display_results

    criteria = run_search_wizard()
    if criteria is None:
        console.print("[dim]Search cancelled.[/dim]")
        return

    results = execute_search_with_spinner(criteria)
    display_results(results, criteria)


def _handle_saved_searches():
    """Browse saved searches — full management interface."""
    from homesearch.tui.saved_browser import show_saved_searches_browser
    show_saved_searches_browser()


def _handle_settings():
    """Open the Settings page with Email, Search Defaults, and About sub-pages."""
    from homesearch.tui.settings import show_settings_menu
    show_settings_menu()


def _handle_web_ui():
    """Stub — Phase 4 implements web UI launch from CLI."""
    console.print("[dim]Web UI launch will be available in a future update.[/dim]")
