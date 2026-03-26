"""Interactive ZIP code browser with spacebar multi-select grouped by city."""

from questionary import checkbox, Choice, Separator

from homesearch.models import ZipInfo
from homesearch.services.zip_service import discover_zip_codes
from homesearch.tui.styles import HOUSE_STYLE, console


def show_zip_browser(location: str, radius_miles: int) -> list[str] | None:
    """Show an interactive ZIP browser for a location.

    Returns selected ZIP codes, empty list if none found, or None if cancelled.
    """
    with console.status("Discovering ZIP codes..."):
        zips = discover_zip_codes(location, radius_miles)

    if not zips:
        console.print("[yellow]No ZIP codes found for that location.[/yellow]")
        return []

    # Cap at 100 most-populated ZIPs (already sorted by population desc)
    zips = zips[:100]

    # Group by city, sorted alphabetically
    by_city: dict[str, list[ZipInfo]] = {}
    for z in zips:
        city_key = f"{z.city}, {z.state}" if z.state else z.city
        by_city.setdefault(city_key, []).append(z)

    # Build questionary choices: Separator per city, then zip choices pre-checked
    choices: list = []
    for city_name in sorted(by_city.keys()):
        city_zips = by_city[city_name]
        choices.append(Separator(f"--- {city_name} ---"))
        for z in city_zips:
            pop = f"pop: {z.population:,}" if z.population else "pop: N/A"
            choices.append(Choice(
                title=f"{z.zipcode} -- {z.city} ({pop})",
                value=z.zipcode,
                checked=True,
            ))

    selected = checkbox(
        "Select ZIP codes (Space=toggle, Enter=confirm):",
        choices=choices,
        style=HOUSE_STYLE,
    ).ask()

    if selected is None:
        return None

    return selected
