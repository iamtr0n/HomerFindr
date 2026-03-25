"""Main menu loop — arrow-key navigation with questionary."""

import questionary

from homesearch.tui.styles import HOUSE_STYLE, console
from homesearch.tui.splash import show_splash


def tui_main():
    """Entry point for the interactive TUI experience.

    Shows splash, then loops the main menu until Exit or Ctrl+C.
    Per D-03: splash on every launch.
    Per D-07: return to menu after any action (while True loop).
    """
    show_splash()
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
    """Run the 15-field search wizard."""
    from homesearch.tui.wizard import run_search_wizard

    criteria = run_search_wizard()
    if criteria is None:
        console.print("[dim]Search cancelled.[/dim]")
        return

    # Search execution will be wired in Plan 04
    console.print(f"[green]Search criteria ready for: {criteria.location}[/green]")
    console.print("[yellow]Search execution coming in next plan...[/yellow]")


def _handle_saved_searches():
    """Basic saved searches view — read-only list for Phase 1."""
    from homesearch import database as db

    db.init_db()
    searches = db.get_saved_searches()

    if not searches:
        console.print("[yellow]No saved searches yet. Run a New Search first.[/yellow]")
        return

    # Show list and let user pick one to run
    choices = [f"{s.name} ({s.criteria.location or 'N/A'})" for s in searches]
    choices.append("\u21a9  Back to menu")

    pick = questionary.select(
        "Saved Searches:",
        choices=choices,
        style=HOUSE_STYLE,
    ).ask()

    if pick is None or "Back to menu" in pick:
        return

    # Find matching search and run it (Plan 04 will add proper execution)
    idx = choices.index(pick)
    if idx < len(searches):
        console.print(f"[cyan]Selected: {searches[idx].name}[/cyan]")
        console.print("[yellow]Search execution coming in Plan 04...[/yellow]")


def _handle_settings():
    """Stub — Phase 2 implements settings."""
    console.print("[dim]Settings will be available in a future update.[/dim]")


def _handle_web_ui():
    """Stub — Phase 4 implements web UI launch from CLI."""
    console.print("[dim]Web UI launch will be available in a future update.[/dim]")
