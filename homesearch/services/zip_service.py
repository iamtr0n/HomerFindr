"""ZIP code discovery: location -> nearby ZIP codes with include/exclude."""

from homesearch.models import ZipInfo


def discover_zip_codes(location: str, radius_miles: int = 25) -> list[ZipInfo]:
    """Given a city/state or ZIP, find all ZIP codes within the radius.

    Uses the uszipcode library which has an offline database - no API calls needed.
    """
    try:
        from uszipcode import SearchEngine
    except ImportError:
        print("[ZIP Discovery] Package not installed. Run: pip install uszipcode")
        return []

    search = SearchEngine()

    # Check if location is a ZIP code
    location_clean = location.strip()
    if location_clean.isdigit() and len(location_clean) == 5:
        center = search.by_zipcode(location_clean)
        if not center or not center.lat:
            return []
        lat, lng = center.lat, center.lng
    else:
        # Try to geocode the city/state
        parsed_city = _parse_city(location_clean)
        parsed_state = _parse_state(location_clean)
        results = search.by_city_and_state(
            city=parsed_city,
            state=parsed_state,
            returns=5,
        )
        # Filter by state to prevent uszipcode cross-state leakage
        if parsed_state and results:
            results = [r for r in results if (r.state or "").upper() == parsed_state.upper()]
        if not results:
            # Fallback: fuzzy city resolution via find_city candidates
            candidates = search.find_city(parsed_city, best_match=False) or [parsed_city]
            for candidate in candidates[:5]:
                r = search.by_city(city=candidate, returns=50)
                if parsed_state:
                    r = [x for x in r if (x.state or "").upper() == parsed_state.upper()]
                if r:
                    results = r
                    break
        if not results:
            return []
        lat, lng = results[0].lat, results[0].lng

    # Search for ZIP codes within radius
    nearby = search.by_coordinates(lat, lng, radius=radius_miles, returns=200)

    zip_infos = []
    for z in nearby:
        if z.zipcode and z.lat:
            zip_infos.append(ZipInfo(
                zipcode=z.zipcode,
                city=z.major_city or z.post_office_city or "",
                state=z.state or "",
                latitude=z.lat,
                longitude=z.lng,
                population=z.population,
                county=z.county or "",
            ))

    # Sort by population descending (most relevant areas first)
    zip_infos.sort(key=lambda x: x.population or 0, reverse=True)
    return zip_infos


# Full state name -> abbreviation mapping (all 50 states + DC)
_STATE_ABBREVS = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
_ABBREV_SET = set(_STATE_ABBREVS.values())  # {"AL", "AK", ...}


def _parse_city(location: str) -> str:
    """Extract city from 'City, State' or 'City State' format."""
    if "," in location:
        return location.split(",")[0].strip()
    tokens = location.strip().split()
    if len(tokens) >= 2:
        last = tokens[-1]
        # Check if last token is a 2-letter abbreviation
        if last.upper() in _ABBREV_SET:
            return " ".join(tokens[:-1])
        # Check if last token(s) form a full state name
        for n in (2, 1):  # Try 2-word states first ("New York"), then 1-word
            if len(tokens) > n:
                candidate = " ".join(tokens[-n:]).lower()
                if candidate in _STATE_ABBREVS:
                    return " ".join(tokens[:-n])
    return location.strip()


def _parse_state(location: str) -> str:
    """Extract state from 'City, State' or 'City State' format."""
    if "," in location:
        parts = location.split(",")
        return parts[1].strip() if len(parts) >= 2 else ""
    tokens = location.strip().split()
    if len(tokens) >= 2:
        last = tokens[-1]
        if last.upper() in _ABBREV_SET:
            return last.upper()
        for n in (2, 1):
            if len(tokens) > n:
                candidate = " ".join(tokens[-n:]).lower()
                if candidate in _STATE_ABBREVS:
                    return _STATE_ABBREVS[candidate]
    return ""
