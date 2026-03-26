"""Highway proximity detection using OpenStreetMap Overpass API."""

import json
import urllib.request
import urllib.parse

_cache: dict[tuple[float, float], tuple[bool, str]] = {}


def check_highway_proximity(lat: float, lon: float, radius_meters: int = 200) -> tuple[bool, str]:
    """Check if coordinates are near a major highway.

    Returns (is_near_highway, road_name). Fails gracefully to (False, "").
    """
    key = (round(lat, 4), round(lon, 4))
    if key in _cache:
        return _cache[key]

    query = f"""[out:json][timeout:5];
way(around:{radius_meters},{lat},{lon})[highway~"motorway|trunk|primary"];
out tags 1;"""

    try:
        url = "https://overpass-api.de/api/interpreter"
        data = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=6) as resp:
            result = json.loads(resp.read())
        elements = result.get("elements", [])
        if elements:
            tags = elements[0].get("tags", {})
            name = tags.get("name") or tags.get("ref") or "major road"
            _cache[key] = (True, name)
            return True, name
        _cache[key] = (False, "")
        return False, ""
    except Exception:
        _cache[key] = (False, "")
        return False, ""
