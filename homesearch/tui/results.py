"""Search execution with animated spinner and results display for HomerFindr TUI."""

import threading
import webbrowser

import questionary
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from homesearch import database as db
from homesearch.models import Listing, SavedSearch, SearchCriteria
from homesearch.services.search_service import get_providers, run_search
from homesearch.tui.styles import (
    COLOR_ADDRESS,
    COLOR_BEDS_BATHS,
    COLOR_PRICE,
    COLOR_SQFT,
    HOUSE_STYLE,
    console,
)


def execute_search_with_spinner(criteria: SearchCriteria) -> tuple[list[Listing], int]:
    """Run search in background thread with animated Rich spinner.

    Per D-17: threading.Thread(daemon=True) for non-blocking.
    Per D-18: Provider name cycling in spinner text.
    CRITICAL: Rich Live must fully exit before any questionary prompt.

    Returns (results, pre_filter_count) so callers can diagnose zero-result causes.
    pre_filter_count is the number of deduplicated listings before client-side filters.
    """
    results: list[Listing] = []
    error: list[Exception] = []
    pre_filter_counts: list[int] = []
    done_event = threading.Event()

    def _search_worker():
        try:
            found = run_search(criteria, use_zip_discovery=True, pre_filter_counts=pre_filter_counts)
            results.extend(found)
        except Exception as e:
            error.append(e)
        finally:
            done_event.set()

    thread = threading.Thread(target=_search_worker, daemon=True)
    thread.start()

    provider_names = [p.name for p in get_providers()]
    if not provider_names:
        provider_names = ["providers"]

    spinners = ["\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f"]
    idx = 0

    with Live(console=console, refresh_per_second=10) as live:
        while not done_event.is_set():
            current = provider_names[idx // 3 % len(provider_names)]
            spin_char = spinners[idx % len(spinners)]
            live.update(
                Text(f"{spin_char}  \U0001f3e0 Searching {current}...", style="bold cyan")
            )
            done_event.wait(timeout=0.1)
            idx += 1

    # Live fully exited — safe for console.print and questionary
    thread.join(timeout=1.0)

    if error:
        console.print(f"[yellow]Warning: search encountered an error — {error[0]}[/yellow]")
        # Per D-19: continue with whatever results we got

    pre_filter_count = pre_filter_counts[0] if pre_filter_counts else 0
    return results, pre_filter_count


def display_results(results: list[Listing], criteria: SearchCriteria, pre_filter_count: int = 0) -> None:
    """Display search results in Rich table with URL opening.

    Per D-13: Colored columns.
    Per D-14: Results count header.
    Per D-15: Arrow-key result selection opens URL.
    Per D-16: Save search prompt after viewing.
    """
    if not results:
        if pre_filter_count > 0:
            # Listings were found but all filtered out — help the user understand why
            console.print(
                f"[yellow]No properties matched your filters "
                f"({pre_filter_count} listing{'s' if pre_filter_count != 1 else ''} found before filtering).[/yellow]"
            )
            console.print("[dim]Active filters that may be too restrictive:[/dim]")
            if criteria.price_min is not None or criteria.price_max is not None:
                lo = f"${criteria.price_min:,}" if criteria.price_min is not None else "any"
                hi = f"${criteria.price_max:,}" if criteria.price_max is not None else "any"
                console.print(f"  [cyan]Price:[/cyan] {lo} – {hi}")
            if criteria.bedrooms_min is not None:
                console.print(f"  [cyan]Bedrooms:[/cyan] {criteria.bedrooms_min}+")
            if criteria.bathrooms_min is not None:
                console.print(f"  [cyan]Bathrooms:[/cyan] {criteria.bathrooms_min}+")
            if criteria.sqft_min is not None or criteria.sqft_max is not None:
                lo = f"{criteria.sqft_min:,}" if criteria.sqft_min is not None else "any"
                hi = f"{criteria.sqft_max:,}" if criteria.sqft_max is not None else "any"
                console.print(f"  [cyan]Sq ft:[/cyan] {lo} – {hi}")
            if criteria.property_types:
                pts = ", ".join(pt.value for pt in criteria.property_types)
                console.print(f"  [cyan]Property type:[/cyan] {pts}")
            if criteria.year_built_min is not None:
                console.print(f"  [cyan]Year built:[/cyan] {criteria.year_built_min}+")
            if criteria.hoa_max is not None:
                label = "No HOA" if criteria.hoa_max == 0.0 else f"up to ${criteria.hoa_max:.0f}/mo"
                console.print(f"  [cyan]HOA:[/cyan] {label}")
            if criteria.has_garage is not None:
                console.print(f"  [cyan]Garage:[/cyan] {'required' if criteria.has_garage else 'none'}")
            if criteria.has_basement is not None:
                console.print(f"  [cyan]Basement:[/cyan] {'required' if criteria.has_basement else 'none'}")
            console.print("[dim]Try running the search again with broader criteria.[/dim]")
        else:
            console.print("[yellow]No properties found matching your criteria.[/yellow]")
            console.print("[dim]Try a different location or broader search area.[/dim]")
        return

    # Count unique providers
    providers = set(r.source for r in results)

    # D-14: Results count header
    console.print(
        Panel(
            f"[bold green]Found {len(results)} listings across {len(providers)} provider{'s' if len(providers) != 1 else ''}[/bold green]",
            border_style="green",
        )
    )

    # D-13: Colored table
    table = Table(
        show_header=True,
        header_style="bold",
        show_lines=True,
        expand=False,
        row_styles=["", "dim"],
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Address", style=COLOR_ADDRESS, min_width=28, no_wrap=True)
    table.add_column("Price", style=COLOR_PRICE, justify="right", width=12)
    table.add_column("Bed/Ba", style=COLOR_BEDS_BATHS, justify="center", width=8)
    table.add_column("SqFt", style=COLOR_SQFT, justify="right", width=8)
    table.add_column("Year", style="dim", justify="center", width=6)
    table.add_column("Source", style="dim", width=10)

    display = results[:50]
    for i, listing in enumerate(display, 1):
        price_str = f"${listing.price:,.0f}" if listing.price else "\u2014"
        bed_bath = f"{listing.bedrooms or '?'}/{listing.bathrooms or '?'}"
        sqft_str = f"{listing.sqft:,}" if listing.sqft else "\u2014"
        addr = listing.address[:40] + ("\u2026" if len(listing.address) > 40 else "")
        table.add_row(
            str(i), addr, price_str, bed_bath, sqft_str,
            str(listing.year_built or "\u2014"), listing.source,
        )

    console.print(table)

    if len(results) > 50:
        console.print(f"[dim]Showing 50 of {len(results)} results.[/dim]")

    # D-15: Arrow-key result selection to open URL
    url_choices = []
    url_map = {}
    for i, listing in enumerate(display, 1):
        if listing.source_url:
            label = f"{i}. {listing.address[:40]}"
            url_choices.append(label)
            url_map[label] = listing.source_url

    if url_choices:
        url_choices.append("\u21a9  Back to menu")
        pick = questionary.select(
            "Select a listing to open in browser:",
            choices=url_choices,
            style=HOUSE_STYLE,
        ).ask()

        if pick and "Back to menu" not in pick and pick in url_map:
            webbrowser.open(url_map[pick])

    # D-16: Save this search?
    _offer_save_search(criteria)


def _offer_save_search(criteria: SearchCriteria) -> None:
    """Prompt to save the search after viewing results."""
    save_choice = questionary.select(
        "Save this search?",
        choices=["Yes", "No"],
        style=HOUSE_STYLE,
    ).ask()

    if save_choice and save_choice == "Yes":
        name = questionary.text(
            "Name this search:",
            style=HOUSE_STYLE,
        ).ask()

        if name and name.strip():
            db.init_db()
            try:
                search_id = db.save_search(SavedSearch(name=name.strip(), criteria=criteria))
                console.print(f"[green]Saved as '{name.strip()}' (ID: {search_id})[/green]")
            except Exception as e:
                console.print(f"[red]Could not save: {e}[/red]")
