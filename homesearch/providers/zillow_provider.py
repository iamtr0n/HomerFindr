"""Provider scraping Zillow's embedded Next.js search data. Free, no API key."""

import json
import re
import time
import traceback
from typing import Optional

from homesearch.models import Listing, ListingType, SearchCriteria
from homesearch.providers.base import BaseProvider

_LISTING_TYPE_PATH = {
    ListingType.SALE: "for_sale",
    ListingType.RENT: "for_rent",
    ListingType.SOLD: "recently_sold",
    ListingType.COMING_SOON: "for_sale",
    ListingType.PENDING: "for_sale",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        if isinstance(val, str):
            val = re.sub(r"[^\d.]", "", val)
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    f = _safe_float(val)
    return int(f) if f is not None else None


class ZillowProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "zillow"

    def search(self, criteria: SearchCriteria, on_progress=None, on_partial=None, on_error=None) -> list[Listing]:
        try:
            import httpx
        except ImportError:
            print("[Zillow] httpx not installed. Run: pip install httpx")
            return []

        locations = self._build_locations(criteria)
        types_to_run = criteria.listing_types if criteria.listing_types else [criteria.listing_type]
        # Dedupe type paths (coming_soon and sale both map to for_sale)
        seen_paths = set()
        unique_types = []
        for lt in types_to_run:
            path = _LISTING_TYPE_PATH.get(lt, "for_sale")
            if path not in seen_paths:
                seen_paths.add(path)
                unique_types.append((lt, path))

        all_listings: list[Listing] = []
        total = len(locations)

        for idx, location in enumerate(locations, 1):
            if on_progress:
                on_progress(idx, total, location, len(all_listings))
            for lt, path in unique_types:
                try:
                    time.sleep(2.5)  # Be respectful — Zillow rate-limits aggressively
                    batch = self._fetch_zip(httpx, location, lt, path)
                    all_listings.extend(batch)
                    if on_partial and batch:
                        on_partial(batch)
                except Exception as e:
                    if on_error:
                        on_error(location, e)
                    print(f"[Zillow] Error for {location}: {e}")
                    continue

        return all_listings

    def _fetch_zip(self, httpx, zip_code: str, listing_type: ListingType, path: str) -> list[Listing]:
        url = f"https://www.zillow.com/homes/{path}/{zip_code}_rb/"
        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=20) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                print(f"[Zillow] HTTP {resp.status_code} for {zip_code}")
                return []

            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
                resp.text,
                re.DOTALL,
            )
            if not match:
                print(f"[Zillow] No __NEXT_DATA__ for {zip_code} — may be blocked")
                return []

            data = json.loads(match.group(1))
            return self._parse_results(data, listing_type, zip_code)

    def _parse_results(self, data: dict, listing_type: ListingType, zip_code: str) -> list[Listing]:
        listings: list[Listing] = []
        try:
            page_props = data.get("props", {}).get("pageProps", {})
            state = page_props.get("searchPageState", {}) or page_props.get("gdpClientCache", {})
            cat1 = state.get("cat1", {})
            search_results = cat1.get("searchResults", {})
            items = search_results.get("listResults") or search_results.get("mapResults") or []

            for item in items:
                listing = self._item_to_listing(item, listing_type, zip_code)
                if listing:
                    listings.append(listing)
        except Exception:
            traceback.print_exc()
        return listings

    def _item_to_listing(self, item: dict, listing_type: ListingType, zip_code: str) -> Optional[Listing]:
        try:
            zpid = str(item.get("zpid") or item.get("id") or "")
            if not zpid:
                return None

            address = item.get("address") or item.get("streetAddress") or ""
            city = item.get("addressCity") or ""
            state = item.get("addressState") or ""
            zip_val = str(item.get("addressZipcode") or zip_code)

            if not address:
                return None

            price = _safe_float(item.get("unformattedPrice") or item.get("price"))

            beds = _safe_int(item.get("beds") or item.get("bedrooms"))
            baths = _safe_float(item.get("baths") or item.get("bathrooms"))
            sqft = _safe_int(item.get("area") or item.get("livingArea"))

            lat_lng = item.get("latLong") or {}
            lat = _safe_float(lat_lng.get("latitude") if isinstance(lat_lng, dict) else item.get("latitude"))
            lng = _safe_float(lat_lng.get("longitude") if isinstance(lat_lng, dict) else item.get("longitude"))

            # Photo
            photo_url = item.get("imgSrc") or ""
            if not photo_url and item.get("miniCardPhotos"):
                photo_url = item["miniCardPhotos"][0].get("url", "")

            # Listing URL
            detail_url = item.get("detailUrl") or ""
            if detail_url and not detail_url.startswith("http"):
                detail_url = f"https://www.zillow.com{detail_url}"

            days_on = _safe_int(item.get("daysOnZillow") or item.get("daysOnMarket"))

            # Property type
            raw_type = (item.get("homeType") or "").upper()
            prop_type = "single_family"
            if "CONDO" in raw_type or "APARTMENT" in raw_type:
                prop_type = "condo"
            elif "TOWNHOUSE" in raw_type or "TOWNHOME" in raw_type:
                prop_type = "townhouse"
            elif "MULTI" in raw_type:
                prop_type = "multi_family"
            elif "LAND" in raw_type or "LOT" in raw_type:
                prop_type = "land"

            # Extra info from hdpData (available on some results)
            hdp = item.get("hdpData") or {}
            home_info = hdp.get("homeInfo") or {} if isinstance(hdp, dict) else {}
            year_built = _safe_int(home_info.get("yearBuilt"))
            description = home_info.get("description") or ""
            hoa = _safe_float(home_info.get("hoaFee"))
            lot_sqft = _safe_int(home_info.get("lotAreaValue"))
            if lot_sqft and home_info.get("lotAreaUnit") == "acres":
                lot_sqft = int(lot_sqft * 43560)

            # Garage / basement hints from description
            desc_lower = description.lower()
            has_garage = True if "garage" in desc_lower else None
            has_basement = True if any(w in desc_lower for w in ("basement", "lower level", "finished lower")) else None

            lt_value = listing_type.value if hasattr(listing_type, "value") else str(listing_type)
            # Override if Zillow flags it as pending/coming soon
            status = (item.get("statusType") or item.get("listingStatus") or "").upper()
            if "PENDING" in status or "UNDER_CONTRACT" in status:
                lt_value = "pending"
            elif "COMING" in status:
                lt_value = "coming_soon"

            return Listing(
                source="zillow",
                source_id=f"z_{zpid}",
                address=address,
                city=city,
                state=state,
                zip_code=zip_val,
                price=price,
                listing_type=lt_value,
                property_type=prop_type,
                bedrooms=beds,
                bathrooms=baths,
                sqft=sqft,
                lot_sqft=lot_sqft,
                year_built=year_built,
                has_garage=has_garage,
                has_basement=has_basement,
                hoa_monthly=hoa,
                latitude=lat,
                longitude=lng,
                photo_url=photo_url,
                source_url=detail_url,
                days_on_mls=days_on,
            )
        except Exception:
            traceback.print_exc()
            return None

    def _build_locations(self, criteria: SearchCriteria) -> list[str]:
        if criteria.zip_codes:
            excluded = set(criteria.excluded_zips)
            return [z for z in criteria.zip_codes if z not in excluded]
        if criteria.location:
            return [criteria.location]
        return []
