"""Provider using the homeharvest package (Realtor.com / MLS data). Free, no API key."""

import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from homesearch.models import Listing, ListingType, SearchCriteria
from homesearch.providers.base import BaseProvider


# Map our ListingType to homeharvest's listing_type parameter
# Valid homeharvest ListingType values: "for_sale", "for_rent", "sold", "pending"
# There is no "coming_soon" in homeharvest — it maps to "pending" (pre-market/pending listings)
_LISTING_TYPE_MAP = {
    ListingType.SALE: "for_sale",
    ListingType.RENT: "for_rent",
    ListingType.SOLD: "sold",
    ListingType.COMING_SOON: "pending",
}


class HomeHarvestProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "realtor"

    def search(self, criteria: SearchCriteria, on_progress=None, on_partial=None) -> list[Listing]:
        try:
            import homeharvest
        except ImportError:
            print("[HomeHarvest] Package not installed. Run: pip install homeharvest")
            return []

        locations = self._build_locations(criteria)
        types_to_run = criteria.listing_types if criteria.listing_types else [criteria.listing_type]

        # Build deduplicated list of homeharvest type strings (preserves order)
        hh_types = [_LISTING_TYPE_MAP.get(lt, "for_sale") for lt in types_to_run]
        hh_types = list(dict.fromkeys(hh_types))

        total = len(locations)
        include_sold = "sold" in hh_types
        listing_type_arg = hh_types[0] if len(hh_types) == 1 else hh_types
        default_lt = hh_types[0]

        all_listings: list[Listing] = []
        lock = threading.Lock()
        completed = [0]

        def _fetch_one(args):
            idx, location = args
            # Stagger 3 parallel workers so requests don't all fire at once
            time.sleep((idx % 3) * 0.6)
            try:
                time.sleep(1.5)  # Rate limiting - be respectful
                df = homeharvest.scrape_property(
                    location=location,
                    listing_type=listing_type_arg,
                    past_days=30 if include_sold else None,
                )
                batch: list[Listing] = []
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        listing = self._row_to_listing(row, default_lt)
                        if listing:
                            batch.append(listing)
                return location, batch
            except Exception:
                traceback.print_exc()
                return location, []

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_map = {
                executor.submit(_fetch_one, (i, loc)): loc
                for i, loc in enumerate(locations)
            }
            for future in as_completed(future_map):
                try:
                    location, batch = future.result()
                except Exception as e:
                    traceback.print_exc()
                    location, batch = future_map[future], []
                with lock:
                    all_listings.extend(batch)
                    completed[0] += 1
                    if on_progress:
                        on_progress(completed[0], total, location, len(all_listings))
                    if on_partial and batch:
                        on_partial(list(batch))

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
            import pandas as pd
            # Normalize: replace all pandas NA values with None for safe Python operations
            row = {k: (None if (v is not None and _is_na(v)) else v) for k, v in row.items()}

            address_parts = []
            for col in ["street", "street_address"]:
                if row.get(col):
                    address_parts.append(str(row[col]))
                    break

            city = str(row.get("city") or "")
            state = str(row.get("state") or "")
            zip_code = str(row.get("zip_code") or "")

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
            price = _safe_float(_coalesce(row.get("list_price"), row.get("price"), row.get("sold_price")))
            beds = _safe_int(_coalesce(row.get("beds"), row.get("bedrooms")))
            baths = _safe_float(_coalesce(row.get("baths"), row.get("bathrooms"), row.get("full_baths")))
            sqft = _safe_int(_coalesce(row.get("sqft"), row.get("square_feet")))
            lot_sqft = _safe_int(row.get("lot_sqft"))
            year_built = _safe_int(row.get("year_built"))
            stories = _safe_int(row.get("stories"))
            hoa = _safe_float(row.get("hoa_fee"))
            lat = _safe_float(row.get("latitude"))
            lon = _safe_float(row.get("longitude"))
            photo = str(_coalesce(row.get("primary_photo"), row.get("img_src")) or "")
            if not photo:
                alt = str(_coalesce(row.get("alt_photos")) or "")
                if alt:
                    photo = alt.split(", ")[0]

            # Garage / basement detection from description
            desc = str(_coalesce(row.get("description"), row.get("text")) or "").lower()
            has_garage = None
            has_basement = None
            garage_spaces = None
            try:
                _pg = bool(_coalesce(row.get("parking_garage")) or False)
            except (TypeError, ValueError):
                _pg = False
            if _pg or "garage" in desc:
                has_garage = True
            if "basement" in desc:
                has_basement = True

            # Fireplace / AC / heat type / pool detection from description
            has_fireplace = True if "fireplace" in desc else None
            has_ac = None
            if "central air" in desc or "central a/c" in desc or "central ac" in desc:
                has_ac = True
            elif "window unit" in desc or "no a/c" in desc or "no ac" in desc or "no air" in desc:
                has_ac = False
            heat_type = None
            if "gas heat" in desc or "natural gas" in desc or "gas furnace" in desc:
                heat_type = "gas"
            elif "electric heat" in desc or "electric furnace" in desc or "heat pump" in desc:
                heat_type = "electric"
            elif "radiant" in desc:
                heat_type = "radiant"
            elif "forced air" in desc:
                heat_type = "forced air"
            has_pool = True if ("pool" in desc and "pool table" not in desc and "carpool" not in desc) else None

            # School data extraction
            from homesearch.services.school_service import get_school_rating_from_row
            school_rating, school_district = get_school_rating_from_row(row)

            # Raw house style (e.g. "CAPE_COD", "RANCH", "COLONIAL")
            raw_style = str(row.get("style", "") or "").strip()
            house_style = raw_style.lower().replace(" ", "_") if raw_style else None

            # Property type mapping
            ptype = str(raw_style or row.get("property_type", "") or "").lower()
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
                has_fireplace=has_fireplace,
                has_ac=has_ac,
                heat_type=heat_type,
                has_pool=has_pool,
                house_style=house_style,
                school_rating=school_rating,
                school_district=school_district,
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


def _is_na(val) -> bool:
    """Safely check if a value is pandas NA / NaN without raising TypeError."""
    try:
        import pandas as pd
        return bool(pd.isna(val))
    except (TypeError, ValueError):
        return False


def _coalesce(*vals):
    """Return first value that is not None and not pandas NA."""
    import pandas as pd
    for v in vals:
        try:
            if v is not None and not pd.isna(v):
                return v
        except (TypeError, ValueError):
            if v is not None:
                return v
    return None


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        import math
        import pandas as pd
        if pd.isna(val):
            return None
        f = float(val)
        return f if not math.isnan(f) else None
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    f = _safe_float(val)
    return int(f) if f is not None else None
