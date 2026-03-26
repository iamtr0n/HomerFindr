"""15-field search wizard with arrow-key navigation for HomerFindr TUI."""

from typing import Optional

import questionary
from rich.panel import Panel
from rich.table import Table

from homesearch.models import ListingType, PropertyType, SearchCriteria
from homesearch.tui.styles import HOUSE_STYLE, console


# ---------------------------------------------------------------------------
# Parser helpers
# ---------------------------------------------------------------------------

def _parse_price_range(choice: str) -> tuple[Optional[int], Optional[int]]:
    """Map price range label to (price_min, price_max)."""
    if choice == "Any":
        return (None, None)
    mapping = {
        "Under $100k":     (None, 100_000),
        "$100k - $200k":   (100_000, 200_000),
        "$200k - $300k":   (200_000, 300_000),
        "$300k - $400k":   (300_000, 400_000),
        "$400k - $500k":   (400_000, 500_000),
        "$500k - $750k":   (500_000, 750_000),
        "$750k - $1M":     (750_000, 1_000_000),
        "$1M - $1.5M":     (1_000_000, 1_500_000),
        "Over $1.5M":      (1_500_000, None),
    }
    return mapping.get(choice, (None, None))


def _parse_multi_price(selections: list[str]) -> tuple[Optional[int], Optional[int]]:
    """Combine multiple price range selections into a single (price_min, price_max)."""
    range_map = {
        "Under $200k":    (None, 200_000),
        "$200k - $350k":  (200_000, 350_000),
        "$350k - $500k":  (350_000, 500_000),
        "$500k - $750k":  (500_000, 750_000),
        "$750k - $1M":    (750_000, 1_000_000),
        "Over $1M":       (1_000_000, None),
    }
    mins = []
    maxes = []
    for sel in selections:
        if sel == "Custom range":
            continue
        bounds = range_map.get(sel)
        if bounds:
            lo, hi = bounds
            if lo is not None:
                mins.append(lo)
            if hi is not None:
                maxes.append(hi)
    price_min = min(mins) if mins else None
    price_max = max(maxes) if maxes else None
    return price_min, price_max


def _parse_sqft_range(choice: str) -> tuple[Optional[int], Optional[int]]:
    """Map square footage label to (sqft_min, sqft_max)."""
    if choice == "Any":
        return (None, None)
    mapping = {
        "Under 1,000":     (None, 1_000),
        "1,000 - 1,500":   (1_000, 1_500),
        "1,500 - 2,000":   (1_500, 2_000),
        "2,000 - 3,000":   (2_000, 3_000),
        "3,000 - 4,000":   (3_000, 4_000),
        "Over 4,000":      (4_000, None),
    }
    return mapping.get(choice, (None, None))


def _parse_lot_range(choice: str) -> tuple[Optional[int], Optional[int]]:
    """Map lot size label to (lot_sqft_min, lot_sqft_max)."""
    if choice == "Any":
        return (None, None)
    mapping = {
        "Under 5,000 sqft":       (None, 5_000),
        "5,000 - 10,000 sqft":    (5_000, 10_000),
        "10,000 - 20,000 sqft":   (10_000, 20_000),
        "Over 20,000 sqft":       (20_000, None),
        "Over 1 acre":            (43_560, None),
    }
    return mapping.get(choice, (None, None))


def _parse_year(choice: str) -> Optional[int]:
    """Map year built label to year_built_min (None for Any)."""
    if choice == "Any":
        return None
    mapping = {
        "2020+":        2020,
        "2010+":        2010,
        "2000+":        2000,
        "1990+":        1990,
        "1980+":        1980,
        "1970 or older": None,
    }
    return mapping.get(choice, None)


def _parse_hoa(choice: str) -> Optional[float]:
    """Map HOA label to hoa_max (None for Any/No limit)."""
    if choice in ("Any / No limit",):
        return None
    mapping = {
        "No HOA ($0)":    0.0,
        "Up to $100/mo":  100.0,
        "Up to $200/mo":  200.0,
        "Up to $300/mo":  300.0,
        "Up to $500/mo":  500.0,
    }
    return mapping.get(choice, None)


# ---------------------------------------------------------------------------
# Summary panel
# ---------------------------------------------------------------------------

def _display_summary(criteria: SearchCriteria) -> None:
    """Render a Rich table panel showing all non-default criteria."""
    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column("Field", style="dim", min_width=18)
    table.add_column("Value", style="white")

    def add(field: str, value) -> None:
        if value is not None and value != "" and value != [] and value != 0.0:
            table.add_row(field, str(value))

    # Listing type is always set
    table.add_row("Listing type", criteria.listing_type.value)

    if criteria.property_types:
        table.add_row("Property type", ", ".join(pt.value for pt in criteria.property_types))

    if criteria.house_styles:
        table.add_row("House styles", ", ".join(s.replace("_", " ").title() for s in criteria.house_styles))

    add("Location", criteria.location)
    add("Radius", f"{criteria.radius_miles} miles")

    if criteria.zip_codes:
        table.add_row("ZIP codes", f"{len(criteria.zip_codes)} selected")
    if criteria.excluded_zips:
        table.add_row("Excluded ZIPs", ", ".join(criteria.excluded_zips))

    if criteria.price_min is not None or criteria.price_max is not None:
        lo = f"${criteria.price_min:,}" if criteria.price_min is not None else "Any"
        hi = f"${criteria.price_max:,}" if criteria.price_max is not None else "Any"
        table.add_row("Price range", f"{lo} - {hi}")

    add("Min bedrooms", criteria.bedrooms_min)
    add("Min bathrooms", criteria.bathrooms_min)

    if criteria.sqft_min is not None or criteria.sqft_max is not None:
        lo = f"{criteria.sqft_min:,}" if criteria.sqft_min is not None else "Any"
        hi = f"{criteria.sqft_max:,}" if criteria.sqft_max is not None else "Any"
        table.add_row("Square footage", f"{lo} - {hi}")

    if criteria.lot_sqft_min is not None or criteria.lot_sqft_max is not None:
        lo = f"{criteria.lot_sqft_min:,}" if criteria.lot_sqft_min is not None else "Any"
        hi = f"{criteria.lot_sqft_max:,}" if criteria.lot_sqft_max is not None else "Any"
        table.add_row("Lot size", f"{lo} - {hi}")

    add("Year built min", criteria.year_built_min)
    add("Min stories", criteria.stories_min)

    if criteria.has_basement is not None:
        table.add_row("Basement", "Required" if criteria.has_basement else "No basement")
    if criteria.has_garage is not None:
        table.add_row("Garage", "Required" if criteria.has_garage else "No garage")
    add("Min garage spaces", criteria.garage_spaces_min)

    if criteria.has_fireplace is not None:
        table.add_row("Fireplace", "Required" if criteria.has_fireplace else "No fireplace")
    if criteria.has_ac is not None:
        table.add_row("AC", "Required" if criteria.has_ac else "No AC")
    if criteria.heat_type is not None:
        table.add_row("Heat type", criteria.heat_type.title())
    if criteria.has_pool is not None:
        table.add_row("Pool", "Required" if criteria.has_pool else "No pool")

    if criteria.hoa_max is not None:
        label = "$0 (No HOA)" if criteria.hoa_max == 0.0 else f"Up to ${criteria.hoa_max:.0f}/mo"
        table.add_row("HOA max", label)

    console.print(Panel(table, title="[bold cyan]Search Summary[/bold cyan]", border_style="cyan"))


# ---------------------------------------------------------------------------
# Main wizard
# ---------------------------------------------------------------------------

def run_search_wizard() -> SearchCriteria | None:
    """Run the 15-field interactive search wizard.

    Navigable entirely with arrow keys and Enter except for the location field
    (city/ZIP typing). Returns a SearchCriteria on success, None if cancelled.
    """
    while True:
        result = _run_wizard_once()
        if result is None:
            # User cancelled mid-wizard
            return None
        criteria, action = result
        if action == "yes":
            return criteria
        if action == "cancel":
            return None
        # action == "edit" — loop back to start


def _run_wizard_once() -> tuple[SearchCriteria, str] | None:
    """Execute the wizard fields once. Returns (criteria, action) or None on cancel."""
    from homesearch.tui.zip_browser import show_zip_browser

    # ------------------------------------------------------------------
    # 1. Listing Type (required — no instruction hint)
    # ------------------------------------------------------------------
    listing_answer = questionary.select(
        "Listing type:",
        choices=["For Sale", "For Rent", "Recently Sold", "Coming Soon"],
        style=HOUSE_STYLE,
    ).ask()
    if listing_answer is None:
        return None
    listing_type_map = {
        "For Sale": ListingType.SALE,
        "For Rent": ListingType.RENT,
        "Recently Sold": ListingType.SOLD,
        "Coming Soon": ListingType.COMING_SOON,
    }
    listing_type = listing_type_map[listing_answer]

    # ------------------------------------------------------------------
    # 2. Property Type
    # ------------------------------------------------------------------
    prop_answer = questionary.select(
        "Property type:",
        choices=["Any", "Single Family", "Condo", "Townhouse", "Multi-Family", "Commercial", "Land"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if prop_answer is None:
        return None
    prop_map = {
        "Single Family": PropertyType.SINGLE_FAMILY,
        "Condo": PropertyType.CONDO,
        "Townhouse": PropertyType.TOWNHOUSE,
        "Multi-Family": PropertyType.MULTI_FAMILY,
        "Commercial": PropertyType.COMMERCIAL,
        "Land": PropertyType.LAND,
    }
    property_types = [] if prop_answer == "Any" else [prop_map[prop_answer]]

    # ------------------------------------------------------------------
    # 2b. House Style (only shown for single-family or "any")
    # ------------------------------------------------------------------
    house_styles: list[str] = []
    if prop_answer in ("Any", "Single Family"):
        STYLE_CHOICES = [
            "Cape Cod", "Ranch", "Colonial", "Split Level", "Raised Ranch",
            "Contemporary", "Victorian", "Craftsman", "Bi-Level", "Tudor",
            "Mediterranean", "Farmhouse",
        ]
        style_answers = questionary.checkbox(
            "House style(s):",
            choices=STYLE_CHOICES,
            style=HOUSE_STYLE,
            instruction="(Space to select, Enter to skip/confirm)",
        ).ask()
        if style_answers is None:
            return None
        # Map labels to raw style substrings used in homeharvest data
        _style_key_map = {
            "Cape Cod": "cape_cod",
            "Ranch": "ranch",
            "Colonial": "colonial",
            "Split Level": "split_level",
            "Raised Ranch": "raised_ranch",
            "Contemporary": "contemporary",
            "Victorian": "victorian",
            "Craftsman": "craftsman",
            "Bi-Level": "bi_level",
            "Tudor": "tudor",
            "Mediterranean": "mediterranean",
            "Farmhouse": "farmhouse",
        }
        house_styles = [_style_key_map[s] for s in style_answers if s in _style_key_map]

    # ------------------------------------------------------------------
    # 3. Radius (moved before location so it applies to all ZIP browser calls)
    # ------------------------------------------------------------------
    radius_answer = questionary.select(
        "Search radius:",
        choices=["5 miles", "10 miles", "25 miles", "50 miles", "100 miles"],
        default="25 miles",
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if radius_answer is None:
        return None
    radius_miles = int(radius_answer.split()[0])

    # ------------------------------------------------------------------
    # 4. Search Mode + Location + ZIP Discovery
    # ------------------------------------------------------------------
    search_mode = questionary.select(
        "Search mode:",
        choices=["Single area", "Multiple areas (combine ZIP codes)"],
        style=HOUSE_STYLE,
    ).ask()
    if search_mode is None:
        return None

    zip_codes: list[str] = []
    excluded_zips: list[str] = []
    location: str = ""

    if search_mode == "Single area":
        # --- Single area ---
        location_answer = questionary.text(
            "City, State or ZIP code:",
            style=HOUSE_STYLE,
        ).ask()
        if location_answer is None:
            return None
        location = location_answer.strip()
        if not location:
            console.print("[red]Location is required.[/red]")
            return None

        selected = show_zip_browser(location, radius_miles)
        if selected is None:
            return None
        zip_codes = selected
    else:
        # --- Multiple areas ---
        all_locations: list[str] = []
        all_zips: list[str] = []

        while True:
            location_answer = questionary.text(
                "City, State or ZIP code:",
                style=HOUSE_STYLE,
            ).ask()
            if location_answer is None:
                return None
            loc = location_answer.strip()
            if not loc:
                console.print("[red]Location is required.[/red]")
                continue
            all_locations.append(loc)

            selected = show_zip_browser(loc, radius_miles)
            if selected is None:
                return None
            all_zips.extend(selected)

            add_more = questionary.confirm(
                "Add another location?",
                default=False,
                style=HOUSE_STYLE,
            ).ask()
            if add_more is None:
                return None
            if not add_more:
                break

        # Deduplicate while preserving order
        zip_codes = list(dict.fromkeys(all_zips))
        location = all_locations[0] if all_locations else ""
        console.print(
            f"[green]Selected {len(zip_codes)} ZIP codes across "
            f"{len(all_locations)} area(s): {', '.join(all_locations)}[/green]"
        )

    if not zip_codes and not location:
        console.print("[yellow]No ZIP codes found — searching by location name.[/yellow]")

    # ------------------------------------------------------------------
    # 6. Price Range (multi-select)
    # ------------------------------------------------------------------
    PRICE_RANGES = [
        "Under $200k",
        "$200k - $350k",
        "$350k - $500k",
        "$500k - $750k",
        "$750k - $1M",
        "Over $1M",
        "Custom range",
    ]
    price_answers = questionary.checkbox(
        "Price range(s):",
        choices=PRICE_RANGES,
        style=HOUSE_STYLE,
        instruction="(Space to select, Enter to confirm)",
    ).ask()
    if price_answers is None:
        return None
    price_min, price_max = _parse_multi_price(price_answers)
    if "Custom range" in price_answers:
        from rich.prompt import Prompt
        custom_min_str = Prompt.ask("  Min price (Enter to skip)", default="")
        custom_max_str = Prompt.ask("  Max price (Enter to skip)", default="")
        try:
            price_min = int(custom_min_str.strip().replace(",", "").replace("$", "")) if custom_min_str.strip() else None
        except ValueError:
            price_min = None
        try:
            price_max = int(custom_max_str.strip().replace(",", "").replace("$", "")) if custom_max_str.strip() else None
        except ValueError:
            price_max = None

    # ------------------------------------------------------------------
    # 7. Bedrooms
    # ------------------------------------------------------------------
    beds_answer = questionary.select(
        "Bedrooms:",
        choices=["Any", "1+", "2+", "3+", "4+", "5+"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if beds_answer is None:
        return None
    bedrooms_min = None if beds_answer == "Any" else int(beds_answer[0])

    # ------------------------------------------------------------------
    # 8. Bathrooms
    # ------------------------------------------------------------------
    baths_answer = questionary.select(
        "Bathrooms:",
        choices=["Any", "1+", "1.5+", "2+", "2.5+", "3+"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if baths_answer is None:
        return None
    bathrooms_min = None if baths_answer == "Any" else float(baths_answer.rstrip("+"))

    # ------------------------------------------------------------------
    # 9. Square Footage
    # ------------------------------------------------------------------
    sqft_answer = questionary.select(
        "Square footage:",
        choices=["Any", "Under 1,000", "1,000 - 1,500", "1,500 - 2,000", "2,000 - 3,000", "3,000 - 4,000", "Over 4,000"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if sqft_answer is None:
        return None
    sqft_min, sqft_max = _parse_sqft_range(sqft_answer)

    # ------------------------------------------------------------------
    # 10. Lot Size
    # ------------------------------------------------------------------
    lot_answer = questionary.select(
        "Lot size:",
        choices=["Any", "Under 5,000 sqft", "5,000 - 10,000 sqft", "10,000 - 20,000 sqft", "Over 20,000 sqft", "Over 1 acre"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if lot_answer is None:
        return None
    lot_sqft_min, lot_sqft_max = _parse_lot_range(lot_answer)

    # ------------------------------------------------------------------
    # 11. Year Built
    # ------------------------------------------------------------------
    year_answer = questionary.select(
        "Year built:",
        choices=["Any", "2020+", "2010+", "2000+", "1990+", "1980+", "1970 or older"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if year_answer is None:
        return None
    year_built_min = _parse_year(year_answer)

    # ------------------------------------------------------------------
    # 12. Stories / Floors
    # ------------------------------------------------------------------
    stories_answer = questionary.select(
        "Stories:",
        choices=["Any", "1+", "2+", "3+"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if stories_answer is None:
        return None
    stories_min = None if stories_answer == "Any" else int(stories_answer[0])

    # ------------------------------------------------------------------
    # 13. Basement
    # ------------------------------------------------------------------
    basement_answer = questionary.select(
        "Basement:",
        choices=["Don't care", "Must have", "No basement"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if basement_answer is None:
        return None
    basement_map = {"Must have": True, "No basement": False, "Don't care": None}
    has_basement = basement_map[basement_answer]

    # ------------------------------------------------------------------
    # 14. Garage
    # ------------------------------------------------------------------
    garage_answer = questionary.select(
        "Garage:",
        choices=["Don't care", "Must have", "No garage"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if garage_answer is None:
        return None
    garage_map = {"Must have": True, "No garage": False, "Don't care": None}
    has_garage = garage_map[garage_answer]

    garage_spaces_min: Optional[int] = None
    if has_garage is True:
        spaces_answer = questionary.select(
            "Minimum garage spaces:",
            choices=["Any", "1+", "2+", "3+"],
            style=HOUSE_STYLE,
            instruction="(Enter to skip)",
        ).ask()
        if spaces_answer is None:
            return None
        garage_spaces_min = None if spaces_answer == "Any" else int(spaces_answer[0])

    # ------------------------------------------------------------------
    # 15. Fireplace
    # ------------------------------------------------------------------
    fireplace_answer = questionary.select(
        "Fireplace:",
        choices=["Don't care", "Must have", "No fireplace"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if fireplace_answer is None:
        return None
    fireplace_map = {"Must have": True, "No fireplace": False, "Don't care": None}
    has_fireplace = fireplace_map[fireplace_answer]

    # ------------------------------------------------------------------
    # 16. Air Conditioning
    # ------------------------------------------------------------------
    ac_answer = questionary.select(
        "Air Conditioning:",
        choices=["Don't care", "Must have", "No AC"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if ac_answer is None:
        return None
    ac_map = {"Must have": True, "No AC": False, "Don't care": None}
    has_ac = ac_map[ac_answer]

    # ------------------------------------------------------------------
    # 17. Heat Type
    # ------------------------------------------------------------------
    heat_answer = questionary.select(
        "Heat type:",
        choices=["Don't care", "Gas", "Electric", "Radiant", "Forced Air"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if heat_answer is None:
        return None
    heat_type = None if heat_answer == "Don't care" else heat_answer.lower()

    # ------------------------------------------------------------------
    # 18. Pool
    # ------------------------------------------------------------------
    pool_answer = questionary.select(
        "Pool:",
        choices=["Don't care", "Must have", "No pool"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if pool_answer is None:
        return None
    pool_map = {"Must have": True, "No pool": False, "Don't care": None}
    has_pool = pool_map[pool_answer]

    # ------------------------------------------------------------------
    # 19. HOA
    # ------------------------------------------------------------------
    hoa_answer = questionary.select(
        "HOA max:",
        choices=["Any / No limit", "No HOA ($0)", "Up to $100/mo", "Up to $200/mo", "Up to $300/mo", "Up to $500/mo"],
        style=HOUSE_STYLE,
        instruction="(Enter to skip)",
    ).ask()
    if hoa_answer is None:
        return None
    hoa_max = _parse_hoa(hoa_answer)

    # ------------------------------------------------------------------
    # Build criteria
    # ------------------------------------------------------------------
    criteria = SearchCriteria(
        location=location,
        radius_miles=radius_miles,
        zip_codes=zip_codes,
        excluded_zips=excluded_zips,
        listing_type=listing_type,
        property_types=property_types,
        house_styles=house_styles,
        price_min=price_min,
        price_max=price_max,
        bedrooms_min=bedrooms_min,
        bathrooms_min=bathrooms_min,
        sqft_min=sqft_min,
        sqft_max=sqft_max,
        lot_sqft_min=lot_sqft_min,
        lot_sqft_max=lot_sqft_max,
        year_built_min=year_built_min,
        stories_min=stories_min,
        has_basement=has_basement,
        has_garage=has_garage,
        garage_spaces_min=garage_spaces_min,
        hoa_max=hoa_max,
        has_fireplace=has_fireplace,
        has_ac=has_ac,
        heat_type=heat_type,
        has_pool=has_pool,
    )

    # ------------------------------------------------------------------
    # D-12: Summary panel + confirm
    # ------------------------------------------------------------------
    _display_summary(criteria)

    confirm_answer = questionary.select(
        "Search now?",
        choices=["Yes", "Edit", "Cancel"],
        style=HOUSE_STYLE,
    ).ask()
    if confirm_answer is None or confirm_answer == "Cancel":
        return (criteria, "cancel")
    if confirm_answer == "Edit":
        return (criteria, "edit")
    return (criteria, "yes")
