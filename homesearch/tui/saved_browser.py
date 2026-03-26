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
    ns = search.notification_settings
    alert_label = f"Set Alerts  [dim](webhook: {ns.zapier_webhook[:30]}…)[/dim]" if ns.zapier_webhook else "Set Alerts  [dim](no webhook set)[/dim]"
    choices = ["\u2190 Back", "Run Now", alert_label, "Toggle Active/Inactive", "Rename", "Merge ZIPs from another search", "Delete"]
    action = questionary.select(
        f"Action for: {search.name}", choices=choices, style=HOUSE_STYLE
    ).ask()
    if action is None or action == "\u2190 Back":
        return
    if action == "Run Now":
        _run_search_now(search)
    elif action and action.startswith("Set Alerts"):
        _set_alerts(search)
    elif action == "Toggle Active/Inactive":
        _toggle_active(search)
    elif action == "Rename":
        _rename_search(search)
    elif action == "Merge ZIPs from another search":
        _merge_search(search)
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


def _set_alerts(search) -> None:
    """Configure Zapier webhook and alert preferences for this saved search."""
    from homesearch import database as db
    from homesearch.models import NotificationSettings
    from rich.panel import Panel

    ns = search.notification_settings
    current_url = ns.zapier_webhook or ""
    coming_soon = ns.notify_coming_soon_only

    status = f"[green]{current_url}[/green]" if current_url else "[dim]Not set (uses global webhook if configured)[/dim]"
    console.print(Panel(
        f"Webhook: {status}\n"
        f"Coming-soon only: {'[green]Yes[/green]' if coming_soon else '[dim]No — all new listings[/dim]'}",
        title=f"[bold cyan]Alerts: {search.name}[/bold cyan]",
        border_style="cyan",
    ))

    choice = questionary.select(
        "Alert settings:",
        choices=[
            "\u2190 Back",
            "Set webhook URL",
            "Clear webhook URL",
            f"Toggle coming-soon only  (currently: {'On' if coming_soon else 'Off'})",
        ],
        style=HOUSE_STYLE,
    ).ask()
    if choice is None or choice == "\u2190 Back":
        return
    if choice == "Set webhook URL":
        url = questionary.text(
            "Zapier webhook URL (leave blank to use global):",
            default=current_url,
            style=HOUSE_STYLE,
        ).ask()
        if url is not None:
            updated = ns.model_copy(update={"zapier_webhook": url.strip()})
            db.update_search(search.id, notification_settings=updated)
            console.print("[green]Webhook saved.[/green]")
    elif choice == "Clear webhook URL":
        updated = ns.model_copy(update={"zapier_webhook": ""})
        db.update_search(search.id, notification_settings=updated)
        console.print("[green]Webhook cleared — will use global webhook if set.[/green]")
    elif choice.startswith("Toggle coming-soon"):
        updated = ns.model_copy(update={"notify_coming_soon_only": not coming_soon})
        db.update_search(search.id, notification_settings=updated)
        label = "On" if not coming_soon else "Off"
        console.print(f"[green]Coming-soon only: {label}.[/green]")


def _merge_search(search) -> None:
    """Merge ZIP codes from another saved search into this one."""
    from homesearch import database as db

    all_searches = db.get_saved_searches()
    others = [s for s in all_searches if s.id != search.id]
    if not others:
        console.print("[yellow]No other saved searches to merge from.[/yellow]")
        return

    choices = ["\u2190 Back"] + [
        f"{s.name} ({len(s.criteria.zip_codes)} ZIPs, {s.criteria.location or 'N/A'})"
        for s in others
    ]
    pick = questionary.select(
        f"Merge ZIPs from which search into '{search.name}'?",
        choices=choices,
        style=HOUSE_STYLE,
    ).ask()
    if pick is None or pick == "\u2190 Back":
        return

    idx = choices.index(pick) - 1
    source = others[idx]

    existing_zips = set(search.criteria.zip_codes)
    new_zips = [z for z in source.criteria.zip_codes if z not in existing_zips]
    if not new_zips:
        console.print(f"[yellow]No new ZIPs to add — '{source.name}' ZIPs are already in '{search.name}'.[/yellow]")
        return

    merged_zips = list(search.criteria.zip_codes) + new_zips
    updated_criteria = search.criteria.model_copy(update={"zip_codes": merged_zips})
    db.update_search(search.id, criteria_json=updated_criteria.model_dump_json())
    console.print(
        f"[green]Merged {len(new_zips)} ZIPs from '{source.name}' into '{search.name}' "
        f"(total: {len(merged_zips)} ZIPs).[/green]"
    )


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
