"""Interactive ZIP code browser: county selection first, then ZIPs within."""

from questionary import checkbox, Choice, Separator

from homesearch.models import ZipInfo
from homesearch.services.zip_service import discover_zip_codes
from homesearch.tui.styles import HOUSE_STYLE, console


def show_zip_browser(location: str, radius_miles: int) -> list[str] | None:
    """Two-step ZIP browser: pick counties/boroughs first, then individual ZIPs.

    Returns selected ZIP codes, empty list if none found, or None if cancelled.
    """
    with console.status("Discovering ZIP codes..."):
        zips = discover_zip_codes(location, radius_miles)

    if not zips:
        console.print("[yellow]No ZIP codes found for that location.[/yellow]")
        return []

    # Cap at 200 most-populated ZIPs
    zips = zips[:200]

    # --- Step 1: County selection ---
    by_county: dict[str, list[ZipInfo]] = {}
    for z in zips:
        county_key = z.county.strip() if z.county and z.county.strip() else f"{z.city}, {z.state}"
        by_county.setdefault(county_key, []).append(z)

    # Build county choices sorted alphabetically, pre-checked, with zip count
    county_choices = []
    for county_name in sorted(by_county.keys()):
        count = len(by_county[county_name])
        county_choices.append(Choice(
            title=f"{county_name}  ({count} ZIPs)",
            value=county_name,
            checked=True,
        ))

    if len(county_choices) > 1:
        selected_counties = checkbox(
            "Select areas/counties to search (Space=toggle, Enter=confirm, Esc=back):",
            choices=county_choices,
            style=HOUSE_STYLE,
        ).ask()

        if selected_counties is None:
            return None

        if not selected_counties:
            console.print("[yellow]No areas selected.[/yellow]")
            return []

        # Filter ZIPs to only the selected counties
        zips = [z for z in zips if (z.county.strip() if z.county and z.county.strip() else f"{z.city}, {z.state}") in selected_counties]

    # --- Step 2: Individual ZIP selection within chosen counties ---
    by_county_filtered: dict[str, list[ZipInfo]] = {}
    for z in zips:
        county_key = z.county.strip() if z.county and z.county.strip() else f"{z.city}, {z.state}"
        by_county_filtered.setdefault(county_key, []).append(z)

    choices: list = []
    for county_name in sorted(by_county_filtered.keys()):
        county_zips = by_county_filtered[county_name]
        choices.append(Separator(f"── {county_name} ──"))
        for z in county_zips:
            pop = f"pop: {z.population:,}" if z.population else ""
            label = f"{z.zipcode}  {z.city}"
            if pop:
                label += f"  ({pop})"
            choices.append(Choice(title=label, value=z.zipcode, checked=True))

    selected = checkbox(
        "Select ZIP codes (Space=toggle, Enter=confirm, Esc=back):",
        choices=choices,
        style=HOUSE_STYLE,
    ).ask()

    if selected is None:
        return None

    return selected
