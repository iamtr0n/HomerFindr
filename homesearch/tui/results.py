"""Search execution with animated spinner and results display for HomerFindr TUI."""

import threading
import webbrowser

import questionary
from rich.columns import Columns
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


def execute_search_with_spinner(criteria: SearchCriteria) -> tuple[list[Listing], int, list[Listing]]:
    """Run parallel ZIP search with live results table."""
    results: list[Listing] = []
    error: list[Exception] = []
    pre_filter_counts: list[int] = []
    raw_listings_out: list[Listing] = []
    done_event = threading.Event()

    progress: dict = {"current": 0, "total": 0, "location": "", "found": 0}
    partial_listings: list[Listing] = []
    partial_lock = threading.Lock()

    def _on_progress(current: int, total: int, location: str, found: int = 0) -> None:
        progress["current"] = current
        progress["total"] = total
        progress["location"] = location
        progress["found"] = found

    def _on_partial(batch: list[Listing]) -> None:
        with partial_lock:
            partial_listings.extend(batch)

    def _search_worker():
        try:
            found = run_search(
                criteria,
                use_zip_discovery=True,
                pre_filter_counts=pre_filter_counts,
                raw_listings_out=raw_listings_out,
                on_progress=_on_progress,
                on_partial=_on_partial,
            )
            results.extend(found)
        except Exception as e:
            error.append(e)
        finally:
            done_event.set()

    thread = threading.Thread(target=_search_worker, daemon=True)
    thread.start()

    spinners = ["\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f"]
    spin_idx = 0
    bar_width = 20

    from rich.console import Group

    with Live(console=console, refresh_per_second=4) as live:
        while not done_event.is_set():
            cur = progress["current"]
            tot = progress["total"]
            found = progress["found"]
            spin = spinners[spin_idx % len(spinners)]
            spin_idx += 1

            # Progress header
            if tot > 0:
                filled = int(bar_width * cur / tot)
                bar = "█" * filled + "░" * (bar_width - filled)
                pct = int(100 * cur / tot)
                active = min(3, tot - cur)
                parallel_note = f"  [dim]({active} ZIPs in parallel)[/dim]" if active > 1 else ""
                header = Text.from_markup(
                    f"{spin}  [bold cyan]🏠  {cur}/{tot} ZIPs  [{bar}] {pct}%  ·  {found} found[/bold cyan]{parallel_note}"
                )
            else:
                header = Text.from_markup(f"{spin}  [bold cyan]🏠  Discovering search area...[/bold cyan]")

            # Live results preview
            with partial_lock:
                snapshot = sorted(
                    [l for l in partial_listings if l.price],
                    key=lambda l: l.price,
                )[:12]

            if snapshot:
                tbl = Table(show_header=True, header_style="dim cyan", box=None, padding=(0, 1))
                tbl.add_column("Price", style="bold green", min_width=11)
                tbl.add_column("Beds/Ba", style="cyan", min_width=7)
                tbl.add_column("Sqft", style="white", min_width=7)
                tbl.add_column("Address", style="white")
                for l in snapshot:
                    price = f"${l.price:,.0f}"
                    beds = f"{l.bedrooms or '?'}bd/{l.bathrooms or '?'}ba"
                    sqft = f"{l.sqft:,}" if l.sqft else "—"
                    addr = l.address[:44] + ("…" if len(l.address) > 44 else "")
                    tbl.add_row(price, beds, sqft, addr)
                note = Text.from_markup(
                    f"[dim]  Live preview — {len(partial_listings)} raw listings so far (filters apply at end)[/dim]"
                )
                live.update(Group(header, Text(""), tbl, note))
            else:
                live.update(header)

            done_event.wait(timeout=0.25)

    thread.join(timeout=1.0)

    if error:
        console.print(f"[yellow]Warning: search encountered an error — {error[0]}[/yellow]")

    pre_filter_count = pre_filter_counts[0] if pre_filter_counts else 0
    return results, pre_filter_count, raw_listings_out


def display_results(results: list[Listing], criteria: SearchCriteria, pre_filter_count: int = 0, raw_listings: list[Listing] | None = None) -> bool:
    """Interactive results browser. Returns True if user wants a new search."""
    if not results:
        _show_no_results(criteria, pre_filter_count, raw_listings)
        return _ask_new_search()

    providers = set(r.source for r in results)
    max_score = max((l.match_score for l in results), default=0)

    console.print(
        Panel(
            f"[bold green]Found {len(results)} listings[/bold green]  "
            f"[dim]across {len(providers)} provider{'s' if len(providers) != 1 else ''}[/dim]",
            border_style="green",
        )
    )

    # Build selector choices — show key info on each line
    page_size = 50
    offset = 0

    while True:
        page = results[offset:offset + page_size]

        # Batch lookup which listings on this page have been viewed
        page_source_ids = [l.source_id for l in page if l.source_id]
        viewed_ids = db.get_viewed_source_ids(page_source_ids)

        choices = []
        for i, l in enumerate(page, offset + 1):
            star = "⭐" if l.is_gold_star else ("★ " if l.is_starred else "  ")
            viewed = "👁 " if l.source_id in viewed_ids else "   "
            price = f"${l.price:,.0f}" if l.price else "N/A"
            ppsf = f"(${round(l.price / l.sqft):,}/sf)" if l.price and l.sqft else ""
            beds = str(l.bedrooms or "?")
            baths = str(l.bathrooms or "?")
            sqft = f"{l.sqft:,}sqft" if l.sqft else ""
            addr = l.address[:40] + ("…" if len(l.address) > 40 else "")
            score = f"[{l.match_score}/{max_score}]" if max_score > 0 else ""
            dom = ""
            if l.days_on_mls is not None:
                if l.days_on_mls < 7:
                    dom = " 🟢New"
                elif l.days_on_mls > 60:
                    dom = f" 🔴{l.days_on_mls}d"
                elif l.days_on_mls >= 31:
                    dom = f" 🟡{l.days_on_mls}d"
            label = f"{star}{viewed}{price:>10} {ppsf:<12}  {beds}bd/{baths}ba  {sqft:<10}  {addr}  {score}{dom}"
            choices.append(questionary.Choice(title=label, value=i - 1))

        # Navigation options
        if offset + page_size < len(results):
            choices.append(questionary.Choice(title=f"   ↓  Load 50 more  ({len(results) - offset - page_size} remaining)", value="more"))
        choices.append(questionary.Choice(title="   ↩  New search", value="new_search"))
        choices.append(questionary.Choice(title="   ←  Back to main menu", value="exit"))

        pick = questionary.select(
            f"Select a listing to view details  ({len(results)} total):",
            choices=choices,
            style=HOUSE_STYLE,
        ).ask()

        if pick is None or pick == "exit":
            _offer_save_search(criteria)
            return False
        if pick == "new_search":
            _offer_save_search(criteria)
            return True
        if pick == "more":
            offset += page_size
            continue

        # Show detail card for the selected listing
        listing = results[pick]
        action = _show_detail_card(listing, max_score)

        if action == "new_search":
            return True
        if action == "exit":
            return False
        # action == "back" → loop back to selector

    return False


def _show_detail_card(listing: Listing, max_score: int) -> str:
    """Show full listing detail. Returns 'back', 'new_search', or 'exit'."""
    star = "⭐ Perfect Match  " if listing.is_gold_star else ""
    title = f"{star}{listing.address}"

    # Build detail table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="dim", min_width=14)
    table.add_column("Value", style="white")

    def row(field, value):
        if value not in (None, "", 0, "?", "—"):
            table.add_row(field, str(value))

    price_str = f"${listing.price:,.0f}" if listing.price else "—"
    if listing.price and listing.sqft:
        ppsf = round(listing.price / listing.sqft)
        price_str += f"  [dim](${ppsf:,}/sqft)[/dim]"
    row("Price", price_str)

    # DOM indicator
    if listing.days_on_mls is not None:
        dom = listing.days_on_mls
        if dom < 7:
            row("Days on Market", f"[bold green]{dom} days — New listing[/bold green]")
        elif dom >= 31 and dom <= 60:
            row("Days on Market", f"[yellow]{dom} days[/yellow]")
        elif dom > 60:
            row("Days on Market", f"[bold red]{dom} days — may be negotiable[/bold red]")
        else:
            row("Days on Market", f"{dom} days")

    city_state = ", ".join(filter(None, [listing.city, listing.state, listing.zip_code]))
    row("Location", city_state or None)

    beds_baths = f"{listing.bedrooms or '?'} bed  /  {listing.bathrooms or '?'} bath"
    row("Beds / Baths", beds_baths)

    row("Sq Ft", f"{listing.sqft:,}" if listing.sqft else None)
    row("Lot Size", f"{listing.lot_sqft:,} sqft" if listing.lot_sqft else None)
    row("Year Built", listing.year_built)
    row("Stories", listing.stories)

    if listing.house_style:
        row("Style", listing.house_style.replace("_", " ").title())
    row("Garage", "Yes" if listing.has_garage else ("No" if listing.has_garage is False else None))
    row("Basement", "Yes" if listing.has_basement else ("No" if listing.has_basement is False else None))
    row("HOA", f"${listing.hoa_monthly:.0f}/mo" if listing.hoa_monthly else None)
    row("Listing Type", listing.listing_type)

    if max_score > 0:
        score_str = f"{listing.match_score} / {max_score}"
        if listing.is_gold_star:
            score_str += "  ⭐"
        row("Match Score", score_str)

    if listing.match_badges:
        row("Badges", "  ·  ".join(listing.match_badges))

    if listing.near_highway:
        row("⚠ Highway", f"Near {listing.highway_name or 'major road'}")

    if listing.school_rating:
        row("School Rating", f"{listing.school_rating}/10  {listing.school_district or ''}")

    if listing.listing_type == "pending":
        if listing.days_on_mls is not None:
            row("Days Pending", f"{listing.days_on_mls} days on market")
        if listing.agent_name:
            row("Agent", listing.agent_name)
        if listing.agent_phone:
            row("Agent Phone", listing.agent_phone)
        if listing.agent_email:
            row("Agent Email", listing.agent_email)
        if listing.days_on_mls is not None and listing.days_on_mls >= 30:
            table.add_row(
                "[bold yellow]⚠ Warning[/bold yellow]",
                "[bold yellow]High chance this sale is not going through[/bold yellow]\n"
                "[dim]Consider reaching out to the agent directly.[/dim]",
            )

    row("Source", listing.source)

    console.print(Panel(table, title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))

    # Action choices
    action_choices = []
    if listing.source_url:
        action_choices.append(questionary.Choice(title="🔗  Open in browser", value="open"))
    action_choices.append(questionary.Choice(title="←  Back to results", value="back"))
    action_choices.append(questionary.Choice(title="🔍  New search", value="new_search"))
    action_choices.append(questionary.Choice(title="✕  Exit", value="exit"))

    action = questionary.select(
        "",
        choices=action_choices,
        style=HOUSE_STYLE,
    ).ask()

    if action == "open" and listing.source_url:
        webbrowser.open(listing.source_url)
        if listing.source_id:
            db.mark_viewed(listing.source_id)
        # Stay on detail card after opening so they can go back
        return _show_detail_card(listing, max_score)

    return action or "back"


def _ask_new_search() -> bool:
    pick = questionary.select(
        "What next?",
        choices=["🔍  New search", "✕  Exit"],
        style=HOUSE_STYLE,
    ).ask()
    return pick and "New search" in pick


def _diagnose_filters(raw: list[Listing], criteria: SearchCriteria) -> list[tuple[str, int, str]]:
    """For each active filter, count how many raw listings it eliminates. Returns sorted list of (label, count, recommendation)."""
    total = len(raw)
    if not total:
        return []

    hits: list[tuple[str, int, str]] = []

    def _elim(pred) -> int:
        return sum(1 for l in raw if pred(l))

    if criteria.price_min is not None:
        n = _elim(lambda l: l.price is not None and l.price < criteria.price_min)
        if n:
            prices = sorted(l.price for l in raw if l.price is not None)
            suggested = int(prices[0] * 0.95) if prices else None
            rec = f"Try lowering price min to ${suggested:,}" if suggested else "Try removing the price minimum"
            hits.append((f"Price min ${criteria.price_min:,.0f}", n, rec))

    if criteria.price_max is not None:
        n = _elim(lambda l: l.price is not None and l.price > criteria.price_max)
        if n:
            over = sorted(l.price for l in raw if l.price is not None and l.price > criteria.price_max)
            suggested = int(over[len(over) // 2]) if over else None
            rec = f"Try raising price max to ${suggested:,}" if suggested else "Try raising the price maximum"
            hits.append((f"Price max ${criteria.price_max:,.0f}", n, rec))

    if criteria.bedrooms_min:
        n = _elim(lambda l: l.bedrooms is not None and l.bedrooms < criteria.bedrooms_min)
        if n:
            suggested = criteria.bedrooms_min - 1
            rec = f"Try lowering beds to {suggested}+" if suggested > 0 else "Try removing the bed requirement"
            hits.append((f"Beds ≥ {criteria.bedrooms_min}", n, rec))

    if criteria.bathrooms_min:
        n = _elim(lambda l: l.bathrooms is not None and l.bathrooms < criteria.bathrooms_min)
        if n:
            suggested = criteria.bathrooms_min - (0.5 if criteria.bathrooms_min > 1 else 1)
            rec = f"Try lowering baths to {suggested}+" if suggested > 0 else "Try removing the bath requirement"
            hits.append((f"Baths ≥ {criteria.bathrooms_min}", n, rec))

    if criteria.sqft_min:
        n = _elim(lambda l: l.sqft is not None and l.sqft < criteria.sqft_min)
        if n:
            sqfts = sorted(l.sqft for l in raw if l.sqft is not None)
            suggested = int(sqfts[len(sqfts) // 2]) if sqfts else None
            rec = f"Try lowering sqft to {suggested:,}" if suggested else "Try lowering the sqft minimum"
            hits.append((f"Sqft ≥ {criteria.sqft_min:,}", n, rec))

    if criteria.sqft_max:
        n = _elim(lambda l: l.sqft is not None and l.sqft > criteria.sqft_max)
        if n:
            hits.append((f"Sqft ≤ {criteria.sqft_max:,}", n, "Try raising the sqft maximum"))

    if criteria.lot_sqft_min:
        n = _elim(lambda l: l.lot_sqft is not None and l.lot_sqft < criteria.lot_sqft_min)
        if n:
            hits.append((f"Lot ≥ {criteria.lot_sqft_min:,} sqft", n, "Try lowering the lot size minimum"))

    if criteria.lot_sqft_max:
        n = _elim(lambda l: l.lot_sqft is not None and l.lot_sqft > criteria.lot_sqft_max)
        if n:
            lots = sorted(l.lot_sqft for l in raw if l.lot_sqft is not None)
            suggested = int(lots[len(lots) // 2]) if lots else None
            rec = f"Try raising lot max to {suggested:,} sqft" if suggested else "Try raising the lot size maximum"
            hits.append((f"Lot ≤ {criteria.lot_sqft_max:,} sqft", n, rec))

    if criteria.stories_min and criteria.stories_min > 1:
        n = _elim(lambda l: l.stories is not None and l.stories < criteria.stories_min)
        if n:
            hits.append((f"Stories ≥ {criteria.stories_min}", n, "Try lowering to 1+ stories or Any"))

    if criteria.year_built_min:
        n = _elim(lambda l: l.year_built is not None and l.year_built < criteria.year_built_min)
        if n:
            suggested = criteria.year_built_min - 5
            hits.append((f"Built ≥ {criteria.year_built_min}", n, f"Try lowering year built to {suggested}"))

    if criteria.has_basement is True:
        n = _elim(lambda l: l.has_basement is False)
        if n:
            hits.append(("Has basement", n, "Remove the basement requirement"))

    if criteria.has_garage is True:
        n = _elim(lambda l: l.has_garage is False)
        if n:
            hits.append(("Has garage", n, "Remove the garage requirement"))

    if criteria.has_fireplace is True:
        n = _elim(lambda l: l.has_fireplace is False)
        if n:
            hits.append(("Has fireplace", n, "Remove the fireplace requirement"))

    if criteria.has_pool is True:
        n = _elim(lambda l: l.has_pool is False)
        if n:
            hits.append(("Has pool", n, "Remove the pool requirement"))

    if criteria.has_ac is True:
        n = _elim(lambda l: l.has_ac is False)
        if n:
            hits.append(("Has A/C", n, "Remove the A/C requirement"))

    if criteria.hoa_max is not None:
        n = _elim(lambda l: l.hoa_monthly is not None and l.hoa_monthly > criteria.hoa_max)
        if n:
            over = sorted(l.hoa_monthly for l in raw if l.hoa_monthly is not None and l.hoa_monthly > criteria.hoa_max)
            suggested = int(over[0]) if over else None
            rec = f"Try raising HOA max to ${suggested}/mo" if suggested else "Try raising the HOA maximum"
            hits.append((f"HOA ≤ ${criteria.hoa_max:.0f}/mo", n, rec))

    if criteria.property_types:
        pt_vals = [pt.value for pt in criteria.property_types]
        n = _elim(lambda l: l.property_type not in pt_vals)
        if n:
            hits.append(("Property type", n, "Add more property types to your search"))

    if criteria.house_styles:
        def _norm(s): return s.lower().replace("-", "_").replace(" ", "_")
        n = _elim(lambda l: l.house_style is not None and not any(
            _norm(s) in _norm(l.house_style) or _norm(l.house_style) in _norm(s)
            for s in criteria.house_styles
        ))
        if n:
            hits.append(("House style", n, "Add more house styles or remove the style filter"))

    if criteria.heat_type and criteria.heat_type != "any":
        n = _elim(lambda l: l.heat_type is not None and l.heat_type != criteria.heat_type)
        if n:
            hits.append((f"Heat: {criteria.heat_type}", n, "Change heat type to 'Don't care'"))

    hits.sort(key=lambda x: -x[1])
    return hits


def _show_active_criteria(criteria: SearchCriteria) -> None:
    """Print a summary of every active filter — shown whenever results are zero."""
    lines = []
    if criteria.price_min or criteria.price_max:
        lo = f"${criteria.price_min:,.0f}" if criteria.price_min else "Any"
        hi = f"${criteria.price_max:,.0f}" if criteria.price_max else "Any"
        lines.append(f"Price: {lo} – {hi}")
    if criteria.bedrooms_min:
        lines.append(f"Beds: {criteria.bedrooms_min}+")
    if criteria.bathrooms_min:
        lines.append(f"Baths: {criteria.bathrooms_min}+")
    if criteria.sqft_min or criteria.sqft_max:
        lo = f"{criteria.sqft_min:,}" if criteria.sqft_min else "Any"
        hi = f"{criteria.sqft_max:,}" if criteria.sqft_max else "Any"
        lines.append(f"Sqft: {lo} – {hi}")
    if criteria.lot_sqft_min or criteria.lot_sqft_max:
        lo = f"{criteria.lot_sqft_min:,}" if criteria.lot_sqft_min else "Any"
        hi = f"{criteria.lot_sqft_max:,}" if criteria.lot_sqft_max else "Any"
        lines.append(f"Lot: {lo} – {hi} sqft")
    if criteria.year_built_min:
        lines.append(f"Year built: {criteria.year_built_min}+")
    if criteria.stories_min:
        lines.append(f"Stories: {criteria.stories_min}+")
    if criteria.has_basement is True:
        lines.append("Basement: Must have")
    if criteria.has_garage is True:
        lines.append("Garage: Must have")
    if criteria.has_fireplace is True:
        lines.append("Fireplace: Must have")
    if criteria.has_ac is True:
        lines.append("A/C: Must have")
    if criteria.has_pool is True:
        lines.append("Pool: Must have")
    if criteria.hoa_max is not None:
        lines.append(f"HOA max: ${criteria.hoa_max:.0f}/mo")
    if criteria.heat_type and criteria.heat_type != "any":
        lines.append(f"Heat type: {criteria.heat_type}")
    if criteria.property_types:
        lines.append(f"Property type: {', '.join(pt.value for pt in criteria.property_types)}")
    if criteria.house_styles:
        lines.append(f"House styles: {', '.join(s.replace('_', ' ').title() for s in criteria.house_styles)}")
    if lines:
        console.print("\n[dim]Active filters on this search:[/dim]")
        for l in lines:
            console.print(f"  [dim]·[/dim] {l}")


def _show_no_results(criteria: SearchCriteria, pre_filter_count: int, raw_listings: list[Listing] | None = None) -> None:
    if pre_filter_count > 0:
        console.print(
            f"\n[yellow]Found {pre_filter_count} listing{'s' if pre_filter_count != 1 else ''} "
            f"but none passed your filters.[/yellow]"
        )
        if raw_listings:
            diagnosis = _diagnose_filters(raw_listings, criteria)
            if diagnosis:
                console.print("[bold]Filters eliminating the most listings:[/bold]")
                bar_w = 20
                for i, (label, count, rec) in enumerate(diagnosis[:6]):
                    pct = int(100 * count / pre_filter_count)
                    filled = max(1, pct * bar_w // 100) if pct > 0 else 0
                    bar = "█" * filled + "░" * (bar_w - filled)
                    if i == 0:
                        console.print(f"  [bold red]{label:<22}[/bold red]  [{bar}] {count}/{pre_filter_count} eliminated")
                        console.print(f"    [red]↳ {rec}[/red]")
                    else:
                        console.print(f"  [yellow]{label:<22}[/yellow]  [{bar}] {count}/{pre_filter_count} eliminated")
                        console.print(f"    [dim]↳ {rec}[/dim]")
        _show_active_criteria(criteria)
        console.print('\n[dim]Use "Edit a filter" at the search prompt to adjust any of these.[/dim]')
    else:
        console.print("[yellow]No listings returned from providers — nothing to filter.[/yellow]")
        console.print("[dim]This usually means the location wasn't recognized or the provider had a temporary error.[/dim]")
        _show_active_criteria(criteria)


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
