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


_PRICE_MAP = {
    "Under $200k":      (None, 200_000),
    "$200k - $350k":    (200_000, 350_000),
    "$350k - $500k":    (350_000, 500_000),
    "$500k - $750k":    (500_000, 750_000),
    "$750k - $1M":      (750_000, 1_000_000),
    "$1M - $1.25M":     (1_000_000, 1_250_000),
    "$1.25M - $1.5M":   (1_250_000, 1_500_000),
    "Over $1.5M":       (1_500_000, None),
}


def _parse_multi_price(selections: list[str]) -> tuple[Optional[int], Optional[int]]:
    """Combine multiple price range selections into a single (price_min, price_max)."""
    non_custom = [s for s in selections if s != "Custom range"]
    return _combine_ranges(non_custom, _PRICE_MAP)


_SQFT_MAP = {
    "Under 1,000  · studio/condo, ~4 parking spaces":          (None, 1_000),
    "1,000 - 1,500  · starter home, ~1 Starbucks":             (1_000, 1_500),
    "1,500 - 2,000  · avg American home, ~½ tennis court":     (1_500, 2_000),
    "2,000 - 3,000  · spacious family home, ~1 tennis court":  (2_000, 3_000),
    "3,000 - 4,000  · large home, ~½ basketball court":        (3_000, 4_000),
    "Over 4,000  · estate, bigger than a basketball court":    (4_000, None),
}

_LOT_MAP = {
    "Under 5,000 sqft  · urban/condo only, rare in suburbs":    (None, 5_000),
    "5,000 - 10,000 sqft  · typical suburb (Long Island, NJ)":  (5_000, 10_000),
    "10,000 - 20,000 sqft  · ¼ acre, most US suburbs":          (10_000, 20_000),
    "Over 20,000 sqft  · ½ acre+, larger suburban/rural":       (20_000, 43_560),
    "Over 1 acre  · full acre+, rural/estate":                   (43_560, None),
}


def _combine_ranges(selections: list[str], mapping: dict) -> tuple[Optional[int], Optional[int]]:
    """Merge multiple range selections: take the lowest min and highest max."""
    has_open_low = False
    has_open_high = False
    mins, maxes = [], []
    for sel in selections:
        bounds = mapping.get(sel)
        if not bounds:
            continue
        lo, hi = bounds
        if lo is None:
            has_open_low = True
        else:
            mins.append(lo)
        if hi is None:
            has_open_high = True
        else:
            maxes.append(hi)
    final_min = None if has_open_low else (min(mins) if mins else None)
    final_max = None if has_open_high else (max(maxes) if maxes else None)
    return (final_min, final_max)


def _parse_multi_sqft(selections: list[str]) -> tuple[Optional[int], Optional[int]]:
    return _combine_ranges(selections, _SQFT_MAP)


def _parse_multi_lot(selections: list[str]) -> tuple[Optional[int], Optional[int]]:
    return _combine_ranges(selections, _LOT_MAP)


def _parse_sqft_range(choice: str) -> tuple[Optional[int], Optional[int]]:
    """Legacy single-choice wrapper — used by non-wizard callers."""
    if choice in ("Any", ""):
        return (None, None)
    return _parse_multi_sqft([choice])


def _parse_lot_range(choice: str) -> tuple[Optional[int], Optional[int]]:
    """Legacy single-choice wrapper — used by non-wizard callers."""
    if choice in ("Any", ""):
        return (None, None)
    return _parse_multi_lot([choice])


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

    # Listing type(s)
    if criteria.listing_types:
        table.add_row("Listing type", ", ".join(lt.value for lt in criteria.listing_types))
    else:
        table.add_row("Listing type", criteria.listing_type.value)

    if criteria.property_types:
        table.add_row("Property type", ", ".join(pt.value for pt in criteria.property_types))

    if criteria.house_styles:
        table.add_row("House styles", ", ".join(s.replace("_", " ").title() for s in criteria.house_styles))

    add("Location", criteria.location)
    add("Radius", f"{criteria.radius_miles} miles")

    if criteria.zip_codes:
        shown = ", ".join(criteria.zip_codes[:10])
        suffix = f"  +{len(criteria.zip_codes) - 10} more" if len(criteria.zip_codes) > 10 else ""
        table.add_row(f"ZIP codes ({len(criteria.zip_codes)})", shown + suffix)
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
    """Execute the wizard as a step machine with back-navigation on every step."""
    from homesearch.tui.zip_browser import show_zip_browser

    _BACK = "__BACK__"

    # Tracks navigation direction so auto-skip steps know when to propagate back
    _nav = {"going_back": False}

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _s(question: str, choices: list, **kw) -> str | None:
        """select with '← Back' appended at the bottom."""
        return questionary.select(
            question,
            choices=list(choices) + [questionary.Choice("← Back", value=_BACK)],
            style=HOUSE_STYLE,
            **kw,
        ).ask()

    def _c(question: str, choices: list, **kw) -> list | str | None:
        """checkbox with ← Back as the last item. Selecting it goes back."""
        all_choices = list(choices) + [questionary.Choice("← Back", value=_BACK)]
        answers = questionary.checkbox(
            question,
            choices=all_choices,
            style=HOUSE_STYLE,
            instruction="(Space to select, Enter to confirm)",
            **kw,
        ).ask()
        if answers is None:
            return None
        if _BACK in answers:
            return _BACK
        return answers

    # ------------------------------------------------------------------
    # Step definitions — each returns dict | _BACK | None(cancel)
    # ------------------------------------------------------------------

    _lt_map = {
        "For Sale": ListingType.SALE,
        "For Rent": ListingType.RENT,
        "Recently Sold": ListingType.SOLD,
        "Coming Soon": ListingType.COMING_SOON,
        "Pending": ListingType.PENDING,
    }

    def _step_listing_type(s):
        r = _c("Listing type(s):", list(_lt_map.keys()))
        if r is None or r == _BACK:
            return r
        if not r:
            r = ["For Sale"]
        lt_list = [_lt_map[a] for a in r]
        return {"listing_types": lt_list, "listing_type": lt_list[0]}

    _prop_map = {
        "Single Family": PropertyType.SINGLE_FAMILY,
        "Condo": PropertyType.CONDO,
        "Townhouse": PropertyType.TOWNHOUSE,
        "Multi-Family": PropertyType.MULTI_FAMILY,
        "Commercial": PropertyType.COMMERCIAL,
        "Land": PropertyType.LAND,
    }
    _style_key_map = {
        "Cape Cod": "cape_cod", "Ranch": "ranch", "Colonial": "colonial",
        "Split Level": "split_level", "Raised Ranch": "raised_ranch",
        "Contemporary": "contemporary", "Victorian": "victorian",
        "Craftsman": "craftsman", "Bi-Level": "bi_level", "Tudor": "tudor",
        "Mediterranean": "mediterranean", "Farmhouse": "farmhouse",
    }
    _STYLE_CHOICES = [
        questionary.Choice("Cape Cod      · ~1,200–2,000 sqft · steep roof, dormers, symmetrical", value="Cape Cod"),
        questionary.Choice("Ranch         · ~1,000–2,000 sqft · single-story, open floor plan", value="Ranch"),
        questionary.Choice("Colonial      · ~2,000–3,500 sqft · 2-story, symmetrical, shuttered windows", value="Colonial"),
        questionary.Choice("Split Level   · ~1,400–2,400 sqft · staggered floors, garage on lower level", value="Split Level"),
        questionary.Choice("Raised Ranch  · ~1,200–1,800 sqft · ranch elevated above a partial basement", value="Raised Ranch"),
        questionary.Choice("Contemporary  · ~2,000–4,000 sqft · clean lines, large windows, open plan", value="Contemporary"),
        questionary.Choice("Victorian     · ~2,500–4,500 sqft · ornate trim, turrets, wrap-around porch", value="Victorian"),
        questionary.Choice("Craftsman     · ~1,500–2,500 sqft · wide porch, tapered columns, natural wood", value="Craftsman"),
        questionary.Choice("Bi-Level      · ~1,400–2,200 sqft · two floors entered from a mid-level foyer", value="Bi-Level"),
        questionary.Choice("Tudor         · ~2,500–5,000 sqft · steep roof, half-timbering, arched doors", value="Tudor"),
        questionary.Choice("Mediterranean · ~3,000–6,000 sqft · stucco exterior, red tile roof, arched windows", value="Mediterranean"),
        questionary.Choice("Farmhouse     · ~2,000–3,500 sqft · large porch, board & batten, metal roof", value="Farmhouse"),
    ]

    def _step_days_pending(s):
        lts = s.get("listing_types", [])
        if ListingType.PENDING not in lts:
            # Auto-skip: propagate back when user is navigating backward
            return _BACK if _nav["going_back"] else {"days_pending_min": None}
        r = _s(
            "Minimum days pending:",
            ["Any", "7+ days", "14+ days", "30+ days", "45+ days", "60+ days"],
        )
        if r is None or r == _BACK:
            return r
        mapping = {"Any": None, "7+ days": 7, "14+ days": 14, "30+ days": 30, "45+ days": 45, "60+ days": 60}
        return {"days_pending_min": mapping.get(r)}

    def _step_property_type(s):
        r = _s("Property type:", ["Any", "Single Family", "Condo", "Townhouse", "Multi-Family", "Commercial", "Land"])
        if r is None or r == _BACK:
            return r
        pt = [] if r == "Any" else [_prop_map[r]]

        house_styles: list[str] = []
        if r in ("Any", "Single Family"):
            sr = _c("House style(s):", _STYLE_CHOICES)
            if sr is None or sr == _BACK:
                return sr
            house_styles = [_style_key_map[v] for v in sr if v in _style_key_map]

        return {"prop_answer": r, "property_types": pt, "house_styles": house_styles}

    def _step_radius(s):
        r = _s("Search radius:", ["5 miles", "10 miles", "25 miles", "50 miles", "100 miles"])
        if r is None or r == _BACK:
            return r
        return {"radius_miles": int(r.split()[0])}

    def _step_search_mode(s):
        r = _s("Search mode:", ["Single area", "Multiple areas (combine ZIP codes)"])
        if r is None or r == _BACK:
            return r
        return {"search_mode": r}

    def _step_location(s):
        radius_miles = s.get("radius_miles", 25)
        mode = s.get("search_mode", "Single area")

        if mode == "Single area":
            loc_answer = questionary.text("City, State or ZIP code:", style=HOUSE_STYLE).ask()
            if loc_answer is None:
                return _BACK
            location = loc_answer.strip()
            if not location:
                console.print("[red]Location is required.[/red]")
                return _BACK
            selected = show_zip_browser(location, radius_miles)
            if selected is None:
                return _BACK
            return {"location": location, "zip_codes": selected, "excluded_zips": []}

        # Multiple areas
        all_locations: list[str] = []
        all_zips: list[str] = []
        while True:
            loc_answer = questionary.text("City, State or ZIP code:", style=HOUSE_STYLE).ask()
            if loc_answer is None:
                return _BACK
            loc = loc_answer.strip()
            if not loc:
                console.print("[red]Location is required.[/red]")
                continue
            if loc.lower() in [l.lower() for l in all_locations]:
                console.print(f"[yellow]{loc} is already in your list — skipping.[/yellow]")
                continue
            all_locations.append(loc)
            # Ask radius per location in multi-area mode
            r_answer = _s(f"Search radius for {loc}:", ["5 miles", "10 miles", "25 miles", "50 miles", "100 miles"])
            if r_answer is None or r_answer == _BACK:
                all_locations.pop()
                continue
            loc_radius = int(r_answer.split()[0])
            selected = show_zip_browser(loc, loc_radius)
            if selected is None:
                return _BACK
            all_zips.extend(selected)
            add_more = questionary.confirm("Add another location?", default=False, style=HOUSE_STYLE).ask()
            if not add_more:
                break
        zip_codes = list(dict.fromkeys(all_zips))
        location = all_locations[0] if all_locations else ""
        console.print(
            f"[green]Selected {len(zip_codes)} ZIP codes across "
            f"{len(all_locations)} area(s): {', '.join(all_locations)}[/green]"
        )
        return {"location": location, "zip_codes": zip_codes, "excluded_zips": []}

    def _step_price(s):
        r = _c("Price range(s):", list(_PRICE_MAP.keys()) + ["Custom range"])
        if r is None or r == _BACK:
            return r
        price_min, price_max = _parse_multi_price(r)
        if "Custom range" in r:
            from rich.prompt import Prompt
            cmin = Prompt.ask("  Min price (Enter to skip)", default="")
            cmax = Prompt.ask("  Max price (Enter to skip)", default="")
            try:
                price_min = int(cmin.strip().replace(",", "").replace("$", "")) if cmin.strip() else None
            except ValueError:
                price_min = None
            try:
                price_max = int(cmax.strip().replace(",", "").replace("$", "")) if cmax.strip() else None
            except ValueError:
                price_max = None
        return {"price_min": price_min, "price_max": price_max}

    def _step_beds(s):
        r = _s("Bedrooms:", ["Any", "1+", "2+", "3+", "4+", "5+"])
        if r is None or r == _BACK:
            return r
        return {"bedrooms_min": None if r == "Any" else int(r[0])}

    def _step_baths(s):
        r = _s("Bathrooms:", ["Any", "1+", "1.5+", "2+", "2.5+", "3+"])
        if r is None or r == _BACK:
            return r
        return {"bathrooms_min": None if r == "Any" else float(r.rstrip("+"))}

    def _step_sqft(s):
        r = _c("Square footage:", list(_SQFT_MAP.keys()))
        if r is None or r == _BACK:
            return r
        sqft_min, sqft_max = _parse_multi_sqft(r)
        return {"sqft_min": sqft_min, "sqft_max": sqft_max}

    def _step_lot(s):
        r = _c("Lot size:", list(_LOT_MAP.keys()))
        if r is None or r == _BACK:
            return r
        lot_min, lot_max = _parse_multi_lot(r)
        return {"lot_sqft_min": lot_min, "lot_sqft_max": lot_max}

    def _step_year(s):
        r = _s("Year built:", ["Any", "2020+", "2010+", "2000+", "1990+", "1980+", "1970 or older"])
        if r is None or r == _BACK:
            return r
        return {"year_built_min": _parse_year(r)}

    def _step_stories(s):
        r = _s("Stories:", ["Any", "1+", "2+", "3+"])
        if r is None or r == _BACK:
            return r
        return {"stories_min": None if r == "Any" else int(r[0])}

    def _step_basement(s):
        r = _s("Basement:", ["Don't care", "Must have", "No basement"])
        if r is None or r == _BACK:
            return r
        return {"has_basement": {"Must have": True, "No basement": False, "Don't care": None}[r]}

    def _step_garage(s):
        r = _s("Garage:", ["Don't care", "Must have", "No garage"])
        if r is None or r == _BACK:
            return r
        has_garage = {"Must have": True, "No garage": False, "Don't care": None}[r]
        garage_spaces_min = None
        if has_garage is True:
            sr = _s("Minimum garage spaces:", ["Any", "1+", "2+", "3+"])
            if sr is None or sr == _BACK:
                return sr
            garage_spaces_min = None if sr == "Any" else int(sr[0])
        return {"has_garage": has_garage, "garage_spaces_min": garage_spaces_min}

    def _step_fireplace(s):
        r = _s("Fireplace:", ["Don't care", "Must have", "No fireplace"])
        if r is None or r == _BACK:
            return r
        return {"has_fireplace": {"Must have": True, "No fireplace": False, "Don't care": None}[r]}

    def _step_ac(s):
        r = _s("Air Conditioning:", ["Don't care", "Must have", "No AC"])
        if r is None or r == _BACK:
            return r
        return {"has_ac": {"Must have": True, "No AC": False, "Don't care": None}[r]}

    def _step_heat(s):
        r = _s("Heat type:", ["Don't care", "Gas", "Electric", "Radiant", "Forced Air"])
        if r is None or r == _BACK:
            return r
        return {"heat_type": None if r == "Don't care" else r.lower()}

    def _step_pool(s):
        r = _s("Pool:", ["Don't care", "Must have", "No pool"])
        if r is None or r == _BACK:
            return r
        return {"has_pool": {"Must have": True, "No pool": False, "Don't care": None}[r]}

    def _step_hoa(s):
        r = _s("HOA max:", ["Any / No limit", "No HOA ($0)", "Up to $100/mo", "Up to $200/mo", "Up to $300/mo", "Up to $500/mo"])
        if r is None or r == _BACK:
            return r
        return {"hoa_max": _parse_hoa(r)}

    steps = [
        _step_listing_type,
        _step_days_pending,
        _step_property_type,
        _step_radius,
        _step_search_mode,
        _step_location,
        _step_price,
        _step_beds,
        _step_baths,
        _step_sqft,
        _step_lot,
        _step_year,
        _step_stories,
        _step_basement,
        _step_garage,
        _step_fireplace,
        _step_ac,
        _step_heat,
        _step_pool,
        _step_hoa,
    ]

    # ------------------------------------------------------------------
    # Step machine loop
    # ------------------------------------------------------------------
    state: dict = {}
    step_idx = 0

    while step_idx < len(steps):
        result = steps[step_idx](state)
        if result is None:
            return None  # ESC / hard cancel
        if result == _BACK:
            _nav["going_back"] = True
            if step_idx == 0:
                return None  # back on first step = cancel
            step_idx -= 1
        else:
            _nav["going_back"] = False
            state.update(result)
            step_idx += 1

    # ------------------------------------------------------------------
    # Build criteria helper (called each loop iteration)
    # ------------------------------------------------------------------
    def _build_criteria():
        return SearchCriteria(
            location=state.get("location", ""),
            radius_miles=state.get("radius_miles", 25),
            zip_codes=state.get("zip_codes", []),
            excluded_zips=state.get("excluded_zips", []),
            listing_type=state.get("listing_type", ListingType.SALE),
            listing_types=state.get("listing_types", [ListingType.SALE]),
            property_types=state.get("property_types", []),
            house_styles=state.get("house_styles", []),
            price_min=state.get("price_min"),
            price_max=state.get("price_max"),
            bedrooms_min=state.get("bedrooms_min"),
            bathrooms_min=state.get("bathrooms_min"),
            sqft_min=state.get("sqft_min"),
            sqft_max=state.get("sqft_max"),
            lot_sqft_min=state.get("lot_sqft_min"),
            lot_sqft_max=state.get("lot_sqft_max"),
            year_built_min=state.get("year_built_min"),
            stories_min=state.get("stories_min"),
            has_basement=state.get("has_basement"),
            has_garage=state.get("has_garage"),
            garage_spaces_min=state.get("garage_spaces_min"),
            hoa_max=state.get("hoa_max"),
            has_fireplace=state.get("has_fireplace"),
            has_ac=state.get("has_ac"),
            heat_type=state.get("heat_type"),
            has_pool=state.get("has_pool"),
            days_pending_min=state.get("days_pending_min"),
        )

    # Human-readable label for each step index
    _STEP_NAMES = [
        "Listing type", "Days pending", "Property type & style", "Search radius",
        "Search mode", "Location & ZIPs", "Price range", "Bedrooms",
        "Bathrooms", "Square footage", "Lot size", "Year built", "Stories",
        "Basement", "Garage", "Fireplace", "Air Conditioning", "Heat type",
        "Pool", "HOA",
    ]

    def _describe_step(idx: int) -> str:
        """Return a short string showing the current value for step idx."""
        s = state
        if idx == 0:
            lts = s.get("listing_types", [])
            return ", ".join(lt.value for lt in lts) if lts else "For Sale"
        if idx == 1:
            lts = s.get("listing_types", [])
            if ListingType.PENDING not in lts:
                return "(n/a)"
            v = s.get("days_pending_min")
            return f"{v}+ days" if v else "Any"
        if idx == 2:
            pa = s.get("prop_answer", "Any")
            hs = s.get("house_styles", [])
            suffix = f"  ({', '.join(h.replace('_', ' ').title() for h in hs)})" if hs else ""
            return pa + suffix
        if idx == 3:
            return f"{s.get('radius_miles', 25)} miles"
        if idx == 4:
            return s.get("search_mode", "Single area")
        if idx == 5:
            loc = s.get("location", "")
            zips = s.get("zip_codes", [])
            return f"{loc}  ({len(zips)} ZIPs)" if zips else loc or "—"
        if idx == 6:
            lo, hi = s.get("price_min"), s.get("price_max")
            if lo is None and hi is None:
                return "Any"
            return f"{'$' + f'{lo:,.0f}' if lo else 'Any'} – {'$' + f'{hi:,.0f}' if hi else 'Any'}"
        if idx == 7:
            v = s.get("bedrooms_min")
            return f"{v}+" if v else "Any"
        if idx == 8:
            v = s.get("bathrooms_min")
            return f"{v}+" if v else "Any"
        if idx == 9:
            lo, hi = s.get("sqft_min"), s.get("sqft_max")
            if lo is None and hi is None:
                return "Any"
            return f"{f'{lo:,}' if lo else 'Any'} – {f'{hi:,}' if hi else 'Any'} sqft"
        if idx == 10:
            lo, hi = s.get("lot_sqft_min"), s.get("lot_sqft_max")
            if lo is None and hi is None:
                return "Any"
            return f"{f'{lo:,}' if lo else 'Any'} – {f'{hi:,}' if hi else 'Any'} sqft"
        if idx == 11:
            v = s.get("year_built_min")
            return f"{v}+" if v else "Any"
        if idx == 12:
            v = s.get("stories_min")
            return f"{v}+" if v else "Any"
        if idx == 13:
            v = s.get("has_basement")
            return "Must have" if v is True else ("No basement" if v is False else "Don't care")
        if idx == 14:
            v = s.get("has_garage")
            gs = s.get("garage_spaces_min")
            base = "Must have" if v is True else ("No garage" if v is False else "Don't care")
            return f"{base}  ({gs}+ spaces)" if gs and v is True else base
        if idx == 15:
            v = s.get("has_fireplace")
            return "Must have" if v is True else ("No fireplace" if v is False else "Don't care")
        if idx == 16:
            v = s.get("has_ac")
            return "Must have" if v is True else ("No AC" if v is False else "Don't care")
        if idx == 17:
            v = s.get("heat_type")
            return v.title() if v else "Don't care"
        if idx == 18:
            v = s.get("has_pool")
            return "Must have" if v is True else ("No pool" if v is False else "Don't care")
        if idx == 19:
            v = s.get("hoa_max")
            if v is None:
                return "Any"
            return "No HOA ($0)" if v == 0 else f"Up to ${v:.0f}/mo"
        return ""

    # ------------------------------------------------------------------
    # Summary + confirm loop with targeted field editing
    # ------------------------------------------------------------------
    while True:
        criteria = _build_criteria()
        _display_summary(criteria)

        confirm_answer = questionary.select(
            "Search now?",
            choices=["Yes, search!", "Edit a filter...", "Cancel"],
            style=HOUSE_STYLE,
        ).ask()

        if confirm_answer is None or confirm_answer == "Cancel":
            return (criteria, "cancel")
        if confirm_answer == "Yes, search!":
            return (criteria, "yes")

        # Build picker list — all steps with current values
        edit_choices = [
            questionary.Choice(f"{name:<22}  {_describe_step(i)}", value=i)
            for i, name in enumerate(_STEP_NAMES)
        ] + [questionary.Choice("← Back", value=-1)]

        which = questionary.select(
            "Which filter would you like to change?",
            choices=edit_choices,
            style=HOUSE_STYLE,
        ).ask()

        if which is None or which == -1:
            continue

        result = steps[which](state)
        if result is not None and result != _BACK:
            state.update(result)
