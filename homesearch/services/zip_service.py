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
        results = search.by_city_and_state(
            city=_parse_city(location_clean),
            state=_parse_state(location_clean),
            returns=1,
        )
        if not results:
            # Fallback: search by city name alone
            results = search.by_city(city=_parse_city(location_clean), returns=1)
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
            ))

    # Sort by population descending (most relevant areas first)
    zip_infos.sort(key=lambda x: x.population or 0, reverse=True)
    return zip_infos


def _parse_city(location: str) -> str:
    """Extract city from 'City, State' format."""
    parts = location.split(",")
    return parts[0].strip()


def _parse_state(location: str) -> str:
    """Extract state from 'City, State' format."""
    parts = location.split(",")
    if len(parts) >= 2:
        return parts[1].strip()
    return ""
