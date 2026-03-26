"""CLI entrypoint for HomeSearch Aggregator."""

import questionary
import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import Optional

from homesearch import database as db
from homesearch.models import SearchCriteria, ListingType, PropertyType, SavedSearch, Listing
from homesearch.tui.menu import tui_main

app = typer.Typer(
    name="homesearch",
    help="Universal home search aggregator - find your perfect home across all platforms.",
    no_args_is_help=False,
)
saved_app = typer.Typer(help="Manage saved searches.")
app.add_typer(saved_app, name="saved")

console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """HomerFindr - search all real estate platforms at once."""
    if ctx.invoked_subcommand is None:
        tui_main()


@app.command()
def search():
    """Interactive search wizard - find properties with detailed filters."""
    from homesearch.tui.wizard import run_search_wizard
    from homesearch.tui.results import execute_search_with_spinner, display_results

    db.init_db()
    while True:
        criteria = run_search_wizard()
        if criteria is None:
            return

        results, pre_filter_count = execute_search_with_spinner(criteria)
        new_search = display_results(results, criteria, pre_filter_count)
        if not new_search:
            return


def search_interactive():
    """Run the interactive search creation wizard."""
    from homesearch.services.search_service import run_search
    from homesearch.services.zip_service import discover_zip_codes

    console.print("\n[bold]🏠 New Property Search[/bold]\n")

    # 1. Listing type
    lt_choice = Prompt.ask(
        "What are you looking for?",
        choices=["buy", "rent", "sold"],
        default="buy",
    )
    listing_type = {"buy": ListingType.SALE, "rent": ListingType.RENT, "sold": ListingType.SOLD}[lt_choice]

    # 2. Property type
    pt_choice = Prompt.ask(
        "Property type?",
        choices=["any", "house", "condo", "townhouse", "multi", "commercial", "land"],
        default="any",
    )
    property_types = []
    pt_map = {
        "house": PropertyType.SINGLE_FAMILY,
        "condo": PropertyType.CONDO,
        "townhouse": PropertyType.TOWNHOUSE,
        "multi": PropertyType.MULTI_FAMILY,
        "commercial": PropertyType.COMMERCIAL,
        "land": PropertyType.LAND,
    }
    if pt_choice != "any":
        property_types = [pt_map[pt_choice]]

    # 3. Location
    location = Prompt.ask("Location (city, state or ZIP code)")

    # 4. Radius
    radius = IntPrompt.ask("Search radius in miles", default=25)

    # 5. ZIP Discovery
    excluded_zips: list[str] = []
    zip_codes: list[str] = []
    with console.status("Discovering ZIP codes in that area..."):
        zips = discover_zip_codes(location, radius)

    if zips:
        console.print(f"\n[green]Found {len(zips)} ZIP codes in the area:[/green]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("ZIP", style="cyan")
        table.add_column("City")
        table.add_column("State")
        table.add_column("Pop.", justify="right")
        for z in zips[:30]:  # Show top 30
            table.add_row(z.zipcode, z.city, z.state, f"{z.population:,}" if z.population else "N/A")
        console.print(table)

        if len(zips) > 30:
            console.print(f"[dim]... and {len(zips) - 30} more[/dim]")

        exclude_input = Prompt.ask(
            "\nExclude any ZIP codes? (comma-separated, or Enter to include all)",
            default="",
        )
        if exclude_input.strip():
            excluded_zips = [z.strip() for z in exclude_input.split(",")]
            console.print(f"[yellow]Excluding: {', '.join(excluded_zips)}[/yellow]")

        zip_codes = [z.zipcode for z in zips if z.zipcode not in excluded_zips]

    # 6. Price range
    price_min = _ask_optional_int("Min price ($)", None)
    price_max = _ask_optional_int("Max price ($)", None)

    # 7. Beds / Baths
    beds_min = _ask_optional_int("Min bedrooms", None)
    baths_min = _ask_optional_float("Min bathrooms", None)

    # 8. Sq footage
    sqft_min = _ask_optional_int("Min square footage", None)
    sqft_max = _ask_optional_int("Max square footage", None)

    # 9. Lot size
    lot_min = _ask_optional_int("Min lot size (sqft)", None)
    lot_max = _ask_optional_int("Max lot size (sqft)", None)

    # 10. Year built
    year_min = _ask_optional_int("Min year built", None)
    year_max = _ask_optional_int("Max year built", None)

    # 11. Stories
    stories_min = _ask_optional_int("Min floors/stories", None)

    # 12. Basement
    basement = _ask_yes_no_any("Basement?")

    # 13. Garage
    garage = _ask_yes_no_any("Garage?")
    garage_spaces = None
    if garage is True:
        garage_spaces = _ask_optional_int("Min garage spaces", None)

    # 14. HOA
    hoa_max = _ask_optional_float("Max monthly HOA ($)", None)

    criteria = SearchCriteria(
        location=location,
        radius_miles=radius,
        zip_codes=zip_codes,
        excluded_zips=excluded_zips,
        listing_type=listing_type,
        property_types=property_types,
        price_min=price_min,
        price_max=price_max,
        bedrooms_min=beds_min,
        bathrooms_min=baths_min,
        sqft_min=sqft_min,
        sqft_max=sqft_max,
        lot_sqft_min=lot_min,
        lot_sqft_max=lot_max,
        year_built_min=year_min,
        year_built_max=year_max,
        stories_min=stories_min,
        has_basement=basement,
        has_garage=garage,
        garage_spaces_min=garage_spaces,
        hoa_max=hoa_max,
    )

    # Save search?
    save_it = Confirm.ask("\nSave this search for later?", default=True)
    search_id = None
    if save_it:
        name = Prompt.ask("Name this search")
        db.init_db()
        try:
            search_id = db.save_search(SavedSearch(name=name, criteria=criteria))
            console.print(f"[green]Saved as '{name}' (ID: {search_id})[/green]")
        except Exception as e:
            console.print(f"[red]Could not save: {e}[/red]")

    # Run the search
    console.print("\n")
    with console.status("[bold blue]Searching across all platforms...[/bold blue]"):
        results = run_search(criteria, search_id=search_id, use_zip_discovery=False)

    _display_results(results)


@app.command()
def serve():
    """Launch the web UI + API server."""
    import threading
    import time
    import uvicorn
    from homesearch.config import settings
    from homesearch.services.scheduler_service import start_scheduler

    db.init_db()
    start_scheduler()

    url = f"http://{settings.host}:{settings.port}"
    console.print(Panel.fit(
        f"[bold green]🏠 HomerFindr[/bold green]\n"
        f"[dim]Web dashboard:[/dim] [bold cyan]{url}[/bold cyan]\n"
        f"[dim]Press Ctrl+C to stop[/dim]",
        border_style="green",
    ))

    open_browser = Confirm.ask("Open in browser?", default=True)

    if open_browser:
        def _open():
            time.sleep(1.5)
            import subprocess, platform
            if platform.system() == "Darwin":
                subprocess.run(["open", url], capture_output=True)
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(
        "homesearch.api.routes:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="error",
    )


@app.command()
def report():
    """Generate and send the email report now."""
    from homesearch.services.report_service import generate_report, send_email_report, build_html_report

    with console.status("Running all active saved searches..."):
        data = generate_report()

    if not data:
        console.print("[yellow]No active saved searches found. Create one first with 'homesearch search'[/yellow]")
        return

    total_new = sum(len(d["new_listings"]) for d in data.values())
    total_all = sum(d["total"] for d in data.values())
    console.print(f"\n[bold]Report Summary:[/bold] {total_new} new listings, {total_all} total across {len(data)} searches\n")

    for name, d in data.items():
        console.print(f"  [cyan]{name}[/cyan]: {d['total']} total, [green]{len(d['new_listings'])} new[/green]")

    if Confirm.ask("\nSend email report?", default=True):
        success = send_email_report(data)
        if success:
            console.print("[green]Email sent![/green]")
        else:
            console.print("[red]Failed to send email. Check .env SMTP settings.[/red]")


# --- Saved search subcommands ---

@saved_app.command("list")
def saved_list():
    """List all saved searches."""
    db.init_db()
    searches = db.get_saved_searches()

    if not searches:
        console.print("[yellow]No saved searches yet. Run 'homesearch search' to create one.[/yellow]")
        return

    table = Table(title="Saved Searches", show_header=True, header_style="bold")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Location")
    table.add_column("Type")
    table.add_column("Price Range")
    table.add_column("Active", justify="center")
    table.add_column("Last Run")

    for s in searches:
        c = s.criteria
        price = ""
        if c.price_min or c.price_max:
            lo = f"${c.price_min:,}" if c.price_min else "Any"
            hi = f"${c.price_max:,}" if c.price_max else "Any"
            price = f"{lo} - {hi}"

        table.add_row(
            str(s.id),
            s.name,
            c.location or "N/A",
            c.listing_type.value,
            price or "Any",
            "✓" if s.is_active else "✗",
            s.last_run_at.strftime("%Y-%m-%d %H:%M") if s.last_run_at else "Never",
        )

    console.print(table)


@saved_app.command("run")
def saved_run(
    name: Optional[str] = typer.Argument(None, help="Name of saved search to run"),
    all_searches: bool = typer.Option(False, "--all", help="Run all active saved searches"),
):
    """Run a saved search by name, or --all to run all active searches."""
    from homesearch.services.search_service import run_search

    db.init_db()

    if all_searches:
        searches = db.get_saved_searches(active_only=True)
        if not searches:
            console.print("[yellow]No active saved searches.[/yellow]")
            return
        for s in searches:
            console.print(f"\n[bold cyan]Running: {s.name}[/bold cyan]")
            with console.status("Searching..."):
                results = run_search(s.criteria, search_id=s.id)
            _display_results(results)
        return

    if not name:
        console.print("[red]Provide a search name or use --all[/red]")
        return

    search = db.get_saved_search_by_name(name)
    if not search:
        console.print(f"[red]Search '{name}' not found. Use 'homesearch saved list' to see all.[/red]")
        return

    with console.status(f"Running '{search.name}'..."):
        results = run_search(search.criteria, search_id=search.id)

    _display_results(results)


@saved_app.command("delete")
def saved_delete(name: str = typer.Argument(help="Name of saved search to delete")):
    """Delete a saved search."""
    db.init_db()
    search = db.get_saved_search_by_name(name)
    if not search:
        console.print(f"[red]Search '{name}' not found.[/red]")
        return
    if Confirm.ask(f"Delete saved search '{name}'?"):
        db.delete_search(search.id)
        console.print(f"[green]Deleted '{name}'[/green]")


@saved_app.command("toggle")
def saved_toggle(name: str = typer.Argument(help="Name of saved search to toggle active/inactive")):
    """Toggle a saved search active/inactive for daily reports."""
    db.init_db()
    search = db.get_saved_search_by_name(name)
    if not search:
        console.print(f"[red]Search '{name}' not found.[/red]")
        return
    new_state = not search.is_active
    db.update_search(search.id, is_active=new_state)
    state_str = "[green]active[/green]" if new_state else "[yellow]inactive[/yellow]"
    console.print(f"'{name}' is now {state_str}")


# --- Helpers ---

def _display_results(results: list[Listing]):
    """Display search results in a rich table."""
    if not results:
        console.print("[yellow]No properties found matching your criteria.[/yellow]")
        return

    console.print(f"\n[bold green]Found {len(results)} properties:[/bold green]\n")

    table = Table(show_header=True, header_style="bold", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Address", min_width=30)
    table.add_column("Price", justify="right", style="green")
    table.add_column("Bed", justify="center")
    table.add_column("Bath", justify="center")
    table.add_column("SqFt", justify="right")
    table.add_column("Year", justify="center")
    table.add_column("Features")
    table.add_column("Source", style="dim")

    for i, l in enumerate(results[:50], 1):  # Show max 50
        price_str = f"${l.price:,.0f}" if l.price else "N/A"
        features = []
        if l.has_garage:
            features.append("Garage")
        if l.has_basement:
            features.append("Basement")
        if l.stories:
            features.append(f"{l.stories}F")
        if l.hoa_monthly:
            features.append(f"HOA ${l.hoa_monthly:.0f}")

        table.add_row(
            str(i),
            l.address,
            price_str,
            str(l.bedrooms or "?"),
            str(l.bathrooms or "?"),
            f"{l.sqft:,}" if l.sqft else "?",
            str(l.year_built or "?"),
            " | ".join(features) if features else "",
            l.source,
        )

    console.print(table)

    if len(results) > 50:
        console.print(f"[dim]... showing 50 of {len(results)} results. Use web UI to see all.[/dim]")

    # Show URLs
    console.print("\n[bold]Property Links:[/bold]")
    for i, l in enumerate(results[:50], 1):
        if l.source_url:
            console.print(f"  {i}. [link={l.source_url}]{l.source_url}[/link]")


def _ask_optional_int(prompt: str, default) -> Optional[int]:
    val = Prompt.ask(f"{prompt} (Enter to skip)", default="")
    if not val.strip():
        return default
    try:
        return int(val.replace(",", ""))
    except ValueError:
        return default


def _ask_optional_float(prompt: str, default) -> Optional[float]:
    val = Prompt.ask(f"{prompt} (Enter to skip)", default="")
    if not val.strip():
        return default
    try:
        return float(val.replace(",", ""))
    except ValueError:
        return default


def _ask_yes_no_any(prompt: str) -> Optional[bool]:
    choice = Prompt.ask(f"{prompt}", choices=["yes", "no", "any"], default="any")
    if choice == "yes":
        return True
    if choice == "no":
        return False
    return None


if __name__ == "__main__":
    app()
