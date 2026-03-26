"""Saved searches browser — view, run, toggle, rename, and delete."""

from datetime import datetime

import questionary
from rich.panel import Panel
from rich.table import Table

from homesearch.tui.styles import HOUSE_STYLE, console


def show_saved_searches_browser() -> None:
    """Main entry point: display saved searches table and action sub-menu in a loop."""
    from homesearch import database as db

    db.init_db()
    while True:
        searches = db.get_saved_searches()
        if not searches:
            console.print(
                "[yellow]No saved searches yet. Run a search from the main menu to save one.[/yellow]"
            )
            return

        _render_searches_table(searches)

        choices = ["\u2190 Back"] + [
            f"{s.name} ({s.criteria.location or 'N/A'})" for s in searches
        ]
        pick = questionary.select(
            "Select a search:", choices=choices, style=HOUSE_STYLE
        ).ask()
        if pick is None or pick == "\u2190 Back":
            return

        idx = choices.index(pick) - 1  # offset for Back entry
        _show_search_submenu(searches[idx])


def _render_searches_table(searches: list) -> None:
    """Render a Rich table of saved searches with Name, Location, Last Run, Active columns."""
    table = Table(show_header=True, header_style="bold", show_lines=True)
    table.add_column("Name", style="white", min_width=20)
    table.add_column("Location", style="cyan", min_width=16)
    table.add_column("Last Run", style="dim", width=20)
    table.add_column("Active", justify="center", width=8)

    for s in searches:
        last_run = s.last_run_at.strftime("%Y-%m-%d %H:%M") if s.last_run_at else "Never"
        active = "[green]\u2713[/green]" if s.is_active else "[red]\u2717[/red]"
        table.add_row(s.name, s.criteria.location or "N/A", last_run, active)

    console.print(table)


def _show_search_submenu(search) -> None:
    """Show action sub-menu for a selected saved search."""
    choices = ["\u2190 Back", "Run Now", "Toggle Active/Inactive", "Rename", "Delete"]
    action = questionary.select(
        f"Action for: {search.name}", choices=choices, style=HOUSE_STYLE
    ).ask()
    if action is None or action == "\u2190 Back":
        return
    if action == "Run Now":
        _run_search_now(search)
    elif action == "Toggle Active/Inactive":
        _toggle_active(search)
    elif action == "Rename":
        _rename_search(search)
    elif action == "Delete":
        _delete_search(search)


def _run_search_now(search) -> None:
    """Execute a saved search immediately and update last_run_at."""
    from homesearch import database as db
    from homesearch.tui.results import display_results, execute_search_with_spinner

    console.print(f"[cyan]Running: {search.name}[/cyan]")
    results, pre_filter_count, raw_listings = execute_search_with_spinner(search.criteria)
    display_results(results, search.criteria, pre_filter_count=pre_filter_count, raw_listings=raw_listings)
    db.update_search(search.id, last_run_at=datetime.now().isoformat())


def _toggle_active(search) -> None:
    """Toggle a saved search between active and inactive."""
    from homesearch import database as db

    new_state = not search.is_active
    db.update_search(search.id, is_active=new_state)
    label = "active" if new_state else "inactive"
    console.print(f"[green]'{search.name}' is now {label}.[/green]")


def _rename_search(search) -> None:
    """Rename a saved search."""
    new_name = questionary.text(
        "New name:", default=search.name, style=HOUSE_STYLE
    ).ask()
    if new_name and new_name.strip():
        from homesearch import database as db

        db.update_search(search.id, name=new_name.strip())
        console.print(f"[green]Renamed to '{new_name.strip()}'.[/green]")


def _delete_search(search) -> None:
    """Delete a saved search after confirmation (defaults to No)."""
    confirmed = questionary.confirm(
        f"Delete '{search.name}'? This cannot be undone.",
        default=False,
        style=HOUSE_STYLE,
    ).ask()
    if confirmed:
        from homesearch import database as db

        db.delete_search(search.id)
        console.print(f"[green]Deleted '{search.name}'.[/green]")
    else:
        console.print("[dim]Cancelled.[/dim]")
