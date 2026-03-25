"""Provider using the homeharvest package (Realtor.com / MLS data). Free, no API key."""

import time
import traceback

from homesearch.models import Listing, ListingType, SearchCriteria
from homesearch.providers.base import BaseProvider


# Map our ListingType to homeharvest's listing_type parameter
_LISTING_TYPE_MAP = {
    ListingType.SALE: "for_sale",
    ListingType.RENT: "for_rent",
    ListingType.SOLD: "sold",
}


class HomeHarvestProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "realtor"

    def search(self, criteria: SearchCriteria) -> list[Listing]:
        try:
            import homeharvest
        except ImportError:
            print("[HomeHarvest] Package not installed. Run: pip install homeharvest")
            return []

        locations = self._build_locations(criteria)
        listing_type = _LISTING_TYPE_MAP.get(criteria.listing_type, "for_sale")

        all_listings: list[Listing] = []

        for location in locations:
            try:
                time.sleep(1.5)  # Rate limiting - be respectful
                df = homeharvest.scrape_property(
                    location=location,
                    listing_type=listing_type,
                    past_days=30 if criteria.listing_type == ListingType.SOLD else None,
                )

                if df is None or df.empty:
                    continue

                for _, row in df.iterrows():
                    listing = self._row_to_listing(row, listing_type)
                    if listing:
                        all_listings.append(listing)

            except Exception:
                traceback.print_exc()
                continue

        return all_listings

    def _build_locations(self, criteria: SearchCriteria) -> list[str]:
        """Build location strings for homeharvest queries."""
        if criteria.zip_codes:
            # Search specific ZIP codes (excluding any the user excluded)
            excluded = set(criteria.excluded_zips)
            return [z for z in criteria.zip_codes if z not in excluded]
        if criteria.location:
            return [criteria.location]
        return []

    def _row_to_listing(self, row, listing_type: str) -> Listing | None:
        """Convert a homeharvest DataFrame row to our Listing model."""
        try:
            address_parts = []
            for col in ["street", "street_address"]:
                if col in row and row.get(col):
                    address_parts.append(str(row[col]))
                    break

            city = str(row.get("city", "")) if row.get("city") else ""
            state = str(row.get("state", "")) if row.get("state") else ""
            zip_code = str(row.get("zip_code", "")) if row.get("zip_code") else ""

            if not address_parts and not city:
                return None

            address = address_parts[0] if address_parts else ""
            if city:
                address += f", {city}"
            if state:
                address += f", {state}"

            # Build source URL
            mls_id = row.get("mls_id", "") or ""
            property_url = row.get("property_url", "") or ""
            source_url = str(property_url) if property_url else ""
            source_id = str(mls_id) if mls_id else source_url or address

            # Property details
            price = _safe_float(row.get("list_price") or row.get("price") or row.get("sold_price"))
            beds = _safe_int(row.get("beds") or row.get("bedrooms"))
            baths = _safe_float(row.get("baths") or row.get("bathrooms") or row.get("full_baths"))
            sqft = _safe_int(row.get("sqft") or row.get("square_feet"))
            lot_sqft = _safe_int(row.get("lot_sqft"))
            year_built = _safe_int(row.get("year_built"))
            stories = _safe_int(row.get("stories"))
            hoa = _safe_float(row.get("hoa_fee"))
            lat = _safe_float(row.get("latitude"))
            lon = _safe_float(row.get("longitude"))
            photo = str(row.get("primary_photo", "") or row.get("img_src", "") or "")

            # Garage / basement detection from description
            desc = str(row.get("description", "") or row.get("text", "") or "").lower()
            has_garage = None
            has_basement = None
            garage_spaces = None
            if row.get("parking_garage") or "garage" in desc:
                has_garage = True
            if "basement" in desc:
                has_basement = True

            # Property type mapping
            ptype = str(row.get("style", "") or row.get("property_type", "") or "").lower()
            property_type = "single_family"
            if "condo" in ptype:
                property_type = "condo"
            elif "town" in ptype:
                property_type = "townhouse"
            elif "multi" in ptype or "duplex" in ptype:
                property_type = "multi_family"
            elif "land" in ptype or "lot" in ptype:
                property_type = "land"
            elif "commercial" in ptype:
                property_type = "commercial"

            lt = "sale"
            if listing_type == "for_rent":
                lt = "rent"
            elif listing_type == "sold":
                lt = "sold"

            return Listing(
                source="realtor",
                source_id=source_id,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                price=price,
                listing_type=lt,
                property_type=property_type,
                bedrooms=beds,
                bathrooms=baths,
                sqft=sqft,
                lot_sqft=lot_sqft,
                stories=stories,
                has_garage=has_garage,
                garage_spaces=garage_spaces,
                has_basement=has_basement,
                year_built=year_built,
                hoa_monthly=hoa,
                latitude=lat,
                longitude=lon,
                photo_url=photo,
                source_url=source_url,
            )
        except Exception:
            traceback.print_exc()
            return None


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
