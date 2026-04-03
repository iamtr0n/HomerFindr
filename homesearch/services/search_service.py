"""Core search orchestration: fans out to providers, dedupes, filters."""

import math
import re
from datetime import datetime
from typing import Optional

from homesearch.models import Listing, SearchCriteria
from homesearch.providers.base import BaseProvider
from homesearch.providers.homeharvest_provider import HomeHarvestProvider
from homesearch.providers.redfin_provider import RedfinProvider
from homesearch.providers.zillow_provider import ZillowProvider
from homesearch.services.zip_service import discover_zip_codes
from homesearch import database as db
from homesearch.services.road_service import check_highway_proximity


def get_providers() -> list[BaseProvider]:
    """Return all enabled providers."""
    providers: list[BaseProvider] = [
        HomeHarvestProvider(),
        RedfinProvider(),
        ZillowProvider(),
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
    errors: Optional[list] = None,
    pre_filter_counts: Optional[list] = None,
    raw_listings_out: Optional[list] = None,
    on_progress=None,
    on_partial=None,
) -> list[Listing]:
    """Execute a search across all providers, dedupe, filter, and return results.

    If search_id is provided, results are persisted and linked to that saved search.
    If pre_filter_counts is provided (as a list), appends the count of deduplicated
    listings before client-side filtering so callers can diagnose zero-result causes.
    """
    db.init_db()

    # Resolve ZIP codes if needed
    if use_zip_discovery and not criteria.zip_codes and criteria.location:
        criteria = resolve_zip_codes(criteria)

    providers = get_providers()
    all_listings: list[Listing] = []

    # Wrap on_progress to inject running found count
    def _wrapped_progress(current, total, location, found=0):
        if on_progress:
            on_progress(current, total, location, found)

    for provider in providers:
        try:
            zip_errors: list[str] = []

            def _on_error(location: str, exc: Exception) -> None:
                msg = f"{provider.name}/{location}: {exc}"
                print(f"[{provider.name}] ZIP error ({location}): {exc}")
                zip_errors.append(msg)

            results = provider.search(
                criteria,
                on_progress=_wrapped_progress,
                on_partial=on_partial,
                on_error=_on_error,
            )
            all_listings.extend(results)
            if errors is not None and zip_errors:
                errors.extend(zip_errors)
        except Exception as e:
            msg = f"{provider.name}: {e}"
            print(f"[{provider.name}] Error: {e}")
            if errors is not None:
                errors.append(msg)

    # Deduplicate by address — prefer realtor source, enrich from Zillow
    seen_addresses: dict[str, Listing] = {}
    for listing in all_listings:
        key = _normalize_address(listing.address)
        if key not in seen_addresses:
            seen_addresses[key] = listing
        else:
            existing = seen_addresses[key]
            # Always keep realtor as primary; enrich it with any missing Zillow fields
            if existing.source == "realtor" and listing.source == "zillow":
                _enrich_listing(existing, listing)
            elif listing.source == "realtor" and existing.source == "zillow":
                _enrich_listing(listing, existing)
                seen_addresses[key] = listing
            else:
                # Both same source — keep whichever has more data
                if _listing_quality(listing) > _listing_quality(existing):
                    seen_addresses[key] = listing

    deduped = list(seen_addresses.values())

    # Record pre-filter count for caller diagnostics
    if pre_filter_counts is not None:
        pre_filter_counts.append(len(deduped))
    if raw_listings_out is not None:
        raw_listings_out.extend(deduped)

    # Note: school enrichment would go here if a school API were available.
    # Currently school_rating is extracted at the provider level from row data.

    # Apply client-side filters for fields not supported by all providers
    filtered = [l for l in deduped if _passes_filters(l, criteria)]

    # Enrich: highway proximity (only when user opted in AND listing has coords)
    if criteria.avoid_highways:
        for listing in filtered:
            if listing.latitude and listing.longitude:
                near, name = check_highway_proximity(listing.latitude, listing.longitude)
                listing.near_highway = near
                listing.highway_name = name

    # Score and sort results
    perfect = _perfect_score(criteria)
    for listing in filtered:
        score, badges = _score_listing(listing, criteria)
        listing.match_score = score
        listing.match_badges = badges
        listing.is_gold_star = score >= perfect and perfect > 0

    if criteria.avoid_highways:
        filtered.sort(key=lambda l: (
            l.near_highway,
            -(1 if l.is_gold_star else 0),
            -l.match_score,
            l.price or float('inf'),
        ))
    else:
        filtered.sort(key=lambda l: (
            -(1 if l.is_gold_star else 0),
            -l.match_score,
            l.price or float('inf'),
        ))

    # If search_id provided, persist results
    if search_id is not None:
        previous_ids = db.get_previous_listing_ids(search_id)
        for listing in filtered:
            lid, _prev_type, prev_price = db.upsert_listing(listing)
            listing.id = lid
            is_new = lid not in previous_ids
            db.link_search_result(search_id, lid, is_new=is_new)
            # Record price change if listing existed and price moved
            if prev_price is not None and listing.price is not None and listing.price != prev_price:
                db.record_price_change(lid, prev_price, listing.price)
        db.update_search(search_id, last_run_at=datetime.now().isoformat())

    return filtered


def _enrich_listing(primary: Listing, secondary: Listing) -> None:
    """Copy missing fields from secondary into primary (non-destructive enrichment)."""
    for field in ["year_built", "has_basement", "has_garage", "garage_spaces",
                  "has_fireplace", "has_ac", "has_pool", "heat_type",
                  "lot_sqft", "hoa_monthly", "stories", "house_style",
                  "photo_url", "latitude", "longitude"]:
        if not getattr(primary, field, None) and getattr(secondary, field, None):
            setattr(primary, field, getattr(secondary, field))


def _normalize_address(address: str) -> str:
    """Normalize address for dedup comparison."""
    addr = address.lower().strip()
    # Strip ZIP codes — Zillow embeds them, Realtor does not; must remove before comparing
    addr = re.sub(r'\b\d{5}(-\d{4})?\b', '', addr)
    # Remove unit/apartment designators
    addr = re.sub(r'\b(apt|unit|suite|ste|#)\s*\S+', '', addr)
    # Normalize street suffixes
    for old, new in [("street", "st"), ("avenue", "ave"), ("drive", "dr"),
                     ("boulevard", "blvd"), ("road", "rd"), ("lane", "ln"),
                     ("court", "ct"), ("place", "pl"), (".", ""), (",", " ")]:
        addr = addr.replace(old, new)
    # Normalize directionals
    for old, new in [("north", "n"), ("south", "s"), ("east", "e"), ("west", "w"),
                     ("northeast", "ne"), ("northwest", "nw"),
                     ("southeast", "se"), ("southwest", "sw")]:
        addr = addr.replace(f" {old} ", f" {new} ")
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


def _score_listing(listing: Listing, criteria: SearchCriteria) -> tuple[int, list[str]]:
    """Score a listing by how many optional criteria it satisfies. Returns (score, badges)."""
    badges = []

    if criteria.has_garage is True and listing.has_garage is True:
        badges.append("garage")

    if criteria.has_basement is True and listing.has_basement is True:
        badges.append("basement")

    if criteria.has_pool is True and listing.has_pool is True:
        badges.append("pool")

    if criteria.has_fireplace is True and listing.has_fireplace is True:
        badges.append("fireplace")

    if criteria.has_ac is True and listing.has_ac is True:
        badges.append("A/C")

    if criteria.hoa_max is not None and listing.hoa_monthly is not None and listing.hoa_monthly <= criteria.hoa_max:
        if listing.hoa_monthly == 0:
            badges.append("no HOA")
        else:
            badges.append(f"HOA ${listing.hoa_monthly:.0f}")

    beds_ok = criteria.bedrooms_min and listing.bedrooms and listing.bedrooms >= criteria.bedrooms_min
    baths_ok = criteria.bathrooms_min and listing.bathrooms and listing.bathrooms >= criteria.bathrooms_min
    if beds_ok or baths_ok:
        badges.append(f"{listing.bedrooms or '?'}bd/{listing.bathrooms or '?'}ba \u2713")

    if criteria.price_min is not None or criteria.price_max is not None:
        price_ok = True
        if criteria.price_min is not None and (not listing.price or listing.price < criteria.price_min):
            price_ok = False
        if criteria.price_max is not None and (not listing.price or listing.price > criteria.price_max):
            price_ok = False
        if price_ok and listing.price:
            badges.append("price \u2713")

    if criteria.year_built_min and listing.year_built and listing.year_built >= criteria.year_built_min:
        if listing.year_built >= 2020:
            badges.append("new build")

    if criteria.heat_type and criteria.heat_type != "any" and listing.heat_type == criteria.heat_type:
        badges.append(listing.heat_type)

    score = len(badges)
    return score, badges


def _perfect_score(criteria: SearchCriteria) -> int:
    """Count the number of optional criteria that can contribute to the score."""
    count = 0
    if criteria.has_garage is True:
        count += 1
    if criteria.has_basement is True:
        count += 1
    if criteria.has_pool is True:
        count += 1
    if criteria.has_fireplace is True:
        count += 1
    if criteria.has_ac is True:
        count += 1
    if criteria.hoa_max is not None:
        count += 1
    if criteria.bedrooms_min and criteria.bathrooms_min:
        count += 1
    if criteria.price_min is not None or criteria.price_max is not None:
        count += 1
    if criteria.year_built_min:
        count += 1
    if criteria.heat_type and criteria.heat_type != "any":
        count += 1
    return max(count, 1)


def _passes_filters(listing: Listing, criteria: SearchCriteria) -> bool:
    """Client-side filtering for fields providers might not support natively."""
    from homesearch.models import ListingType as _LT

    # Allowlist filter: only show listing types the user requested.
    types_wanted = set(criteria.listing_types) if criteria.listing_types else (
        {criteria.listing_type} if criteria.listing_type else set()
    )
    if types_wanted:
        allowed_strs = {lt.value if hasattr(lt, 'value') else lt for lt in types_wanted}
        if listing.listing_type and listing.listing_type not in allowed_strs:
            return False

    # Numeric filters: reject if value is missing or out of range.
    if criteria.price_min is not None and (listing.price is None or listing.price < criteria.price_min):
        return False
    if criteria.price_max is not None and (listing.price is None or listing.price > criteria.price_max):
        return False

    if criteria.bedrooms_min is not None and (listing.bedrooms is None or listing.bedrooms < criteria.bedrooms_min):
        return False
    if criteria.bathrooms_min is not None and (listing.bathrooms is None or listing.bathrooms < criteria.bathrooms_min):
        return False

    if criteria.sqft_min is not None and (listing.sqft is None or listing.sqft < criteria.sqft_min):
        return False
    if criteria.sqft_max is not None and (listing.sqft is None or listing.sqft > criteria.sqft_max):
        return False

    if criteria.lot_sqft_min is not None and (listing.lot_sqft is None or listing.lot_sqft < criteria.lot_sqft_min):
        return False
    if criteria.lot_sqft_max is not None and (listing.lot_sqft is None or listing.lot_sqft > criteria.lot_sqft_max):
        return False

    if criteria.year_built_min is not None and (listing.year_built is None or listing.year_built < criteria.year_built_min):
        return False
    if criteria.year_built_max is not None and (listing.year_built is None or listing.year_built > criteria.year_built_max):
        return False

    if criteria.stories_min is not None and (listing.stories is None or listing.stories < criteria.stories_min):
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

    if criteria.has_fireplace is True and listing.has_fireplace is False:
        return False

    if criteria.has_ac is True and listing.has_ac is False:
        return False
    if criteria.has_ac is False and listing.has_ac is True:
        return False

    if criteria.heat_type and criteria.heat_type != "any":
        if listing.heat_type and listing.heat_type != criteria.heat_type:
            return False

    if criteria.has_pool is True and listing.has_pool is False:
        return False
    if criteria.has_pool is False and listing.has_pool is True:
        return False

    if criteria.property_types:
        pt_vals = [pt.value for pt in criteria.property_types]
        if listing.property_type is not None and listing.property_type not in pt_vals:
            return False

    # House style filter — fuzzy match (handles hyphens, underscores, spaces)
    if criteria.house_styles:
        def _norm(s): return s.lower().replace("-", "_").replace(" ", "_")
        if listing.house_style is None:
            # strict mode: hide listings where style couldn't be detected
            if criteria.style_strict:
                return False
        else:
            ls = _norm(listing.house_style)
            if not any(_norm(s) in ls or ls in _norm(s) for s in criteria.house_styles):
                return False

    # School rating minimum
    if criteria.school_rating_min and listing.school_rating and listing.school_rating < criteria.school_rating_min:
        return False

    # Days pending minimum (only filters pending listings; other types pass through)
    if criteria.days_pending_min is not None and listing.listing_type == "pending":
        if listing.days_on_mls is None or listing.days_on_mls < criteria.days_pending_min:
            return False

    # ZIP exclusion
    if criteria.excluded_zips and listing.zip_code in criteria.excluded_zips:
        return False

    # Radius check using lat/long (if we have coordinates for both)
    if criteria.zip_codes and listing.latitude and listing.longitude:
        # We check radius from the center of the search area
        pass  # Already filtered by ZIP code discovery

    return True
