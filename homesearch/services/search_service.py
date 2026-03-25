"""Core search orchestration: fans out to providers, dedupes, filters."""

import math
from datetime import datetime
from typing import Optional

from homesearch.models import Listing, SearchCriteria
from homesearch.providers.base import BaseProvider
from homesearch.providers.homeharvest_provider import HomeHarvestProvider
from homesearch.providers.redfin_provider import RedfinProvider
from homesearch.services.zip_service import discover_zip_codes
from homesearch import database as db


def get_providers() -> list[BaseProvider]:
    """Return all enabled providers."""
    providers: list[BaseProvider] = [
        HomeHarvestProvider(),
        RedfinProvider(),
    ]
    return [p for p in providers if p.enabled]


def resolve_zip_codes(criteria: SearchCriteria) -> SearchCriteria:
    """If location is given but no specific ZIP codes, discover them."""
    if criteria.zip_codes or not criteria.location:
        return criteria

    zips = discover_zip_codes(criteria.location, criteria.radius_miles)
    if zips:
        excluded = set(criteria.excluded_zips)
        criteria = criteria.model_copy(update={
            "zip_codes": [z.zipcode for z in zips if z.zipcode not in excluded],
        })
    return criteria


def run_search(
    criteria: SearchCriteria,
    search_id: Optional[int] = None,
    use_zip_discovery: bool = True,
) -> list[Listing]:
    """Execute a search across all providers, dedupe, filter, and return results.

    If search_id is provided, results are persisted and linked to that saved search.
    """
    db.init_db()

    # Resolve ZIP codes if needed
    if use_zip_discovery and not criteria.zip_codes and criteria.location:
        criteria = resolve_zip_codes(criteria)

    providers = get_providers()
    all_listings: list[Listing] = []

    for provider in providers:
        try:
            results = provider.search(criteria)
            all_listings.extend(results)
        except Exception as e:
            print(f"[{provider.name}] Error: {e}")

    # Deduplicate by address (normalized)
    seen_addresses: dict[str, Listing] = {}
    for listing in all_listings:
        key = _normalize_address(listing.address)
        if key not in seen_addresses:
            seen_addresses[key] = listing
        else:
            # Keep the one with more data or prefer realtor (MLS source)
            existing = seen_addresses[key]
            if _listing_quality(listing) > _listing_quality(existing):
                seen_addresses[key] = listing

    deduped = list(seen_addresses.values())

    # Apply client-side filters for fields not supported by all providers
    filtered = [l for l in deduped if _passes_filters(l, criteria)]

    # If search_id provided, persist results
    if search_id is not None:
        previous_ids = db.get_previous_listing_ids(search_id)
        for listing in filtered:
            lid = db.upsert_listing(listing)
            is_new = lid not in previous_ids
            db.link_search_result(search_id, lid, is_new=is_new)
        db.update_search(search_id, last_run_at=datetime.now().isoformat())

    return filtered


def _normalize_address(address: str) -> str:
    """Normalize address for dedup comparison."""
    addr = address.lower().strip()
    for old, new in [("street", "st"), ("avenue", "ave"), ("drive", "dr"),
                     ("boulevard", "blvd"), ("road", "rd"), ("lane", "ln"),
                     ("court", "ct"), ("place", "pl"), (".", ""), (",", " ")]:
        addr = addr.replace(old, new)
    return " ".join(addr.split())


def _listing_quality(listing: Listing) -> int:
    """Score how much data a listing has (for dedup preference)."""
    score = 0
    if listing.price:
        score += 1
    if listing.bedrooms:
        score += 1
    if listing.sqft:
        score += 1
    if listing.photo_url:
        score += 1
    if listing.source_url:
        score += 1
    if listing.year_built:
        score += 1
    if listing.source == "realtor":
        score += 2  # Prefer MLS data
    return score


def _passes_filters(listing: Listing, criteria: SearchCriteria) -> bool:
    """Client-side filtering for fields providers might not support natively."""

    if criteria.price_min and listing.price and listing.price < criteria.price_min:
        return False
    if criteria.price_max and listing.price and listing.price > criteria.price_max:
        return False

    if criteria.bedrooms_min and listing.bedrooms and listing.bedrooms < criteria.bedrooms_min:
        return False
    if criteria.bathrooms_min and listing.bathrooms and listing.bathrooms < criteria.bathrooms_min:
        return False

    if criteria.sqft_min and listing.sqft and listing.sqft < criteria.sqft_min:
        return False
    if criteria.sqft_max and listing.sqft and listing.sqft > criteria.sqft_max:
        return False

    if criteria.lot_sqft_min and listing.lot_sqft and listing.lot_sqft < criteria.lot_sqft_min:
        return False
    if criteria.lot_sqft_max and listing.lot_sqft and listing.lot_sqft > criteria.lot_sqft_max:
        return False

    if criteria.year_built_min and listing.year_built and listing.year_built < criteria.year_built_min:
        return False
    if criteria.year_built_max and listing.year_built and listing.year_built > criteria.year_built_max:
        return False

    if criteria.stories_min and listing.stories and listing.stories < criteria.stories_min:
        return False

    if criteria.has_basement is True and listing.has_basement is False:
        return False
    if criteria.has_basement is False and listing.has_basement is True:
        return False

    if criteria.has_garage is True and listing.has_garage is False:
        return False
    if criteria.has_garage is False and listing.has_garage is True:
        return False

    if criteria.garage_spaces_min and listing.garage_spaces and listing.garage_spaces < criteria.garage_spaces_min:
        return False

    if criteria.hoa_max is not None and listing.hoa_monthly and listing.hoa_monthly > criteria.hoa_max:
        return False

    if criteria.property_types:
        if listing.property_type not in [pt.value for pt in criteria.property_types]:
            return False

    # ZIP exclusion
    if criteria.excluded_zips and listing.zip_code in criteria.excluded_zips:
        return False

    # Radius check using lat/long (if we have coordinates for both)
    if criteria.zip_codes and listing.latitude and listing.longitude:
        # We check radius from the center of the search area
        pass  # Already filtered by ZIP code discovery

    return True
