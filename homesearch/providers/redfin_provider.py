"""Provider using the Redfin stingray API. Free, no API key."""

import time
import traceback

from homesearch.models import Listing, ListingType, SearchCriteria
from homesearch.providers.base import BaseProvider


class RedfinProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "redfin"

    def search(self, criteria: SearchCriteria) -> list[Listing]:
        try:
            from redfin import Redfin
        except ImportError:
            print("[Redfin] Package not installed. Run: pip install redfin")
            return []

        client = Redfin()
        locations = self._build_locations(criteria)
        all_listings: list[Listing] = []

        for location in locations:
            try:
                time.sleep(2)  # Rate limiting
                response = client.search(location)

                if not response or "payload" not in response:
                    continue

                payload = response["payload"]
                exact_match = payload.get("exactMatch")
                if not exact_match:
                    sections = payload.get("sections", [])
                    if not sections:
                        continue
                    rows = sections[0].get("rows", [])
                    if not rows:
                        continue
                    exact_match = rows[0]

                url = exact_match.get("url", "")
                if not url:
                    continue

                time.sleep(1.5)
                region_info = client.meta_property(url, listing_type=self._get_listing_type_num(criteria))

                if not region_info or "payload" not in region_info:
                    continue

                homes = region_info.get("payload", {}).get("homes", [])
                if not homes:
                    continue

                for home in homes:
                    listing = self._home_to_listing(home, criteria)
                    if listing:
                        all_listings.append(listing)

            except Exception:
                traceback.print_exc()
                continue

        return all_listings

    def _build_locations(self, criteria: SearchCriteria) -> list[str]:
        if criteria.zip_codes:
            excluded = set(criteria.excluded_zips)
            return [z for z in criteria.zip_codes if z not in excluded]
        if criteria.location:
            return [criteria.location]
        return []

    def _get_listing_type_num(self, criteria: SearchCriteria) -> int:
        if criteria.listing_type == ListingType.RENT:
            return 2
        if criteria.listing_type == ListingType.SOLD:
            return 3
        return 1  # For sale

    def _home_to_listing(self, home: dict, criteria: SearchCriteria) -> Listing | None:
        try:
            home_data = home.get("homeData", home)
            price_info = home_data.get("priceInfo", {})
            address_info = home_data.get("addressInfo", {})

            address = address_info.get("formattedStreetLine", "")
            city = address_info.get("city", "")
            state = address_info.get("state", "")
            zip_code = str(address_info.get("zip", ""))

            if not address and not city:
                return None

            price = price_info.get("amount")
            if price is None:
                price = home_data.get("price", {}).get("value")

            beds = home_data.get("beds")
            baths = home_data.get("baths")
            sqft = home_data.get("sqFt", {}).get("value") if isinstance(home_data.get("sqFt"), dict) else home_data.get("sqFt")
            lot_sqft = home_data.get("lotSize", {}).get("value") if isinstance(home_data.get("lotSize"), dict) else home_data.get("lotSize")
            year_built = home_data.get("yearBuilt")
            lat = address_info.get("centroid", {}).get("centroid", {}).get("latitude") if address_info.get("centroid") else home_data.get("latLong", {}).get("latitude")
            lon = address_info.get("centroid", {}).get("centroid", {}).get("longitude") if address_info.get("centroid") else home_data.get("latLong", {}).get("longitude")
            hoa = home_data.get("hoaDues")

            photo_url = ""
            photos = home_data.get("photos", home_data.get("staticMapUrl"))
            if isinstance(photos, list) and photos:
                photo_url = photos[0].get("photoUrl", "") if isinstance(photos[0], dict) else str(photos[0])
            elif isinstance(photos, str):
                photo_url = photos

            property_id = str(home_data.get("propertyId", "") or home_data.get("mlsId", {}).get("value", "") or address)
            listing_url = home_data.get("url", "")
            if listing_url and not listing_url.startswith("http"):
                listing_url = f"https://www.redfin.com{listing_url}"

            lt = "sale"
            if criteria.listing_type == ListingType.RENT:
                lt = "rent"
            elif criteria.listing_type == ListingType.SOLD:
                lt = "sold"

            return Listing(
                source="redfin",
                source_id=property_id,
                address=f"{address}, {city}, {state}" if address else city,
                city=city,
                state=state,
                zip_code=zip_code,
                price=_safe_float(price),
                listing_type=lt,
                property_type=_map_property_type(home_data.get("propertyType", "")),
                bedrooms=_safe_int(beds),
                bathrooms=_safe_float(baths),
                sqft=_safe_int(sqft),
                lot_sqft=_safe_int(lot_sqft),
                stories=None,
                has_garage=None,
                garage_spaces=None,
                has_basement=None,
                year_built=_safe_int(year_built),
                hoa_monthly=_safe_float(hoa),
                latitude=_safe_float(lat),
                longitude=_safe_float(lon),
                photo_url=photo_url,
                source_url=listing_url,
            )
        except Exception:
            traceback.print_exc()
            return None


def _map_property_type(ptype) -> str:
    ptype = str(ptype).lower()
    if "condo" in ptype:
        return "condo"
    if "town" in ptype:
        return "townhouse"
    if "multi" in ptype:
        return "multi_family"
    if "land" in ptype or "lot" in ptype:
        return "land"
    return "single_family"


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        import math
        f = float(val)
        return f if not math.isnan(f) else None
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    f = _safe_float(val)
    return int(f) if f is not None else None
