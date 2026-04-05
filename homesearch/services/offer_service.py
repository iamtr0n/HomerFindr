"""Offer estimation service: logical CMA + AI-powered analysis."""

from __future__ import annotations

import statistics
import traceback
from typing import Optional

from homesearch.models import (
    AIOfferEstimate,
    ComparableSale,
    Listing,
    LogicalOffer,
    OfferEstimate,
)


# --- Comp fetching ---

def fetch_comps(listing: Listing, past_days: int = 180) -> list[ComparableSale]:
    """Fetch recently sold comparable homes from homeharvest.

    Filters to same property type, ±1 bed, ±1 bath, sqft within ±35%.
    Returns empty list on failure (never raises).
    """
    try:
        from homeharvest import scrape_property
        import pandas as pd

        location = listing.zip_code or f"{listing.city}, {listing.state}"
        if not location.strip():
            return []

        df = scrape_property(
            location=location,
            listing_type="sold",
            past_days=past_days,
        )
        if df is None or df.empty:
            return []

        comps: list[ComparableSale] = []
        for _, row in df.iterrows():
            try:
                price = _safe_float(row.get("sold_price") or row.get("list_price") or row.get("price"))
                sqft = _safe_int(row.get("sqft") or row.get("square_feet"))
                if not price or price <= 0:
                    continue

                # Property type similarity
                row_type = str(row.get("style") or row.get("property_type") or "").lower()
                listing_type = (listing.property_type or "single_family").lower()
                if not _types_compatible(row_type, listing_type):
                    continue

                # Bedroom/bathroom proximity
                row_beds = _safe_int(row.get("beds") or row.get("bedrooms"))
                row_baths = _safe_float(row.get("full_baths") or row.get("baths") or row.get("bathrooms"))
                if listing.bedrooms and row_beds:
                    if abs(row_beds - listing.bedrooms) > 1:
                        continue
                if listing.bathrooms and row_baths:
                    if abs(row_baths - listing.bathrooms) > 1.5:
                        continue

                # Sqft proximity (±35%)
                if listing.sqft and sqft:
                    ratio = sqft / listing.sqft
                    if ratio < 0.65 or ratio > 1.35:
                        continue

                ppsf = round(price / sqft, 2) if sqft and sqft > 0 else None
                comp = ComparableSale(
                    address=str(row.get("street") or row.get("address") or ""),
                    price=price,
                    sqft=sqft,
                    price_per_sqft=ppsf,
                    bedrooms=row_beds,
                    bathrooms=row_baths,
                    year_built=_safe_int(row.get("year_built")),
                    has_garage=_safe_bool(row.get("garage")),
                    has_basement=_safe_bool(row.get("basement")),
                    days_on_mls=_safe_int(row.get("days_on_market") or row.get("dom")),
                    zip_code=str(row.get("zip_code") or ""),
                )
                comps.append(comp)
            except Exception:
                continue

        # Limit to 20 best comps (closest sqft match)
        if listing.sqft and comps:
            comps.sort(key=lambda c: abs((c.sqft or listing.sqft) - listing.sqft))
        return comps[:20]

    except Exception:
        traceback.print_exc()
        return []


# --- Logical CMA estimate ---

def calculate_logical_offer(listing: Listing, comps: list[ComparableSale]) -> Optional[LogicalOffer]:
    """Pure math CMA: median $/sqft from comps + feature adjustments."""
    if not comps or not listing.sqft:
        return None

    # Collect $/sqft from comps that have sqft data
    ppsf_values = [c.price_per_sqft for c in comps if c.price_per_sqft and c.price_per_sqft > 0]
    if not ppsf_values:
        return None

    median_ppsf = statistics.median(ppsf_values)
    base_value = median_ppsf * listing.sqft
    confidence = "high" if len(ppsf_values) >= 5 else ("medium" if len(ppsf_values) >= 2 else "low")

    # --- Feature adjustments ---
    adjustments: dict[str, float] = {}

    # Garage
    comp_garage_avg = _avg_bool(comps, "has_garage")
    if listing.has_garage is True and comp_garage_avg < 0.5:
        adjustments["garage"] = 12_000.0
    elif listing.has_garage is False and comp_garage_avg >= 0.5:
        adjustments["garage"] = -8_000.0

    # Basement
    comp_basement_avg = _avg_bool(comps, "has_basement")
    if listing.has_basement is True and comp_basement_avg < 0.5:
        adjustments["basement"] = 20_000.0
    elif listing.has_basement is False and comp_basement_avg >= 0.5:
        adjustments["basement"] = -15_000.0

    # Year built difference
    comp_years = [c.year_built for c in comps if c.year_built]
    if comp_years and listing.year_built:
        avg_year = statistics.mean(comp_years)
        year_diff = listing.year_built - avg_year
        adj = year_diff * 1_200.0  # $1,200 per year newer/older
        if abs(adj) > 500:
            adjustments["year_built"] = round(adj, 0)

    # Lot size difference
    comp_lots = [c for c in comps if hasattr(c, "lot_sqft") and getattr(c, "lot_sqft", None)]
    if comp_lots and listing.lot_sqft:
        # Can't get lot_sqft from ComparableSale model — skip for now
        pass

    total_adjustment = sum(adjustments.values())
    estimated_value = base_value + total_adjustment

    # Offer tiers
    offer_low = round(estimated_value * 0.95)
    offer_fair = round(estimated_value * 0.985)
    offer_strong = round(estimated_value * 1.01)

    # Compare listing price to estimate
    listing_price = listing.price or 0
    if listing_price > 0:
        pct_diff = ((listing_price - estimated_value) / estimated_value) * 100
    else:
        pct_diff = 0.0

    if pct_diff < -5:
        assessment = "underpriced"
    elif pct_diff > 5:
        assessment = "overpriced"
    else:
        assessment = "fairly_priced"

    return LogicalOffer(
        estimated_value=round(estimated_value),
        price_per_sqft_comps=round(median_ppsf, 2),
        offer_low=offer_low,
        offer_fair=offer_fair,
        offer_strong=offer_strong,
        value_assessment=assessment,
        price_vs_estimate_pct=round(pct_diff, 1),
        comp_count=len(ppsf_values),
        confidence=confidence,
        adjustments={k: int(v) for k, v in adjustments.items()},
    )


# --- AI estimate ---

def calculate_ai_offer(listing: Listing, comps: list[ComparableSale], logical: Optional[LogicalOffer]) -> Optional[AIOfferEstimate]:
    """Call Claude to produce a narrative offer recommendation."""
    from homesearch.config import settings

    if not settings.anthropic_api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Build comp summary
        comp_summary = _build_comp_summary(comps, logical)
        listing_summary = _build_listing_summary(listing)

        prompt = f"""You are a real estate expert helping a buyer decide how much to offer on a home.

LISTING:
{listing_summary}

COMPARABLE SOLD HOMES (last 180 days, same area):
{comp_summary}

Based on this data, provide a JSON response with these exact fields:
{{
  "suggested_offer": <number — your single best offer price>,
  "offer_range_low": <number — floor of reasonable offer range>,
  "offer_range_high": <number — ceiling of reasonable offer range>,
  "confidence": <"high" | "medium" | "low">,
  "reasoning": <2-3 sentence explanation of the offer recommendation>,
  "market_assessment": <1 sentence describing current market conditions based on comp data>,
  "negotiation_tips": [<2-3 actionable tips as strings>],
  "red_flags": [<any concerns about the listing, empty array if none>]
}}

Return only valid JSON, no markdown, no extra text."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())

        return AIOfferEstimate(
            suggested_offer=float(data["suggested_offer"]),
            offer_range_low=float(data["offer_range_low"]),
            offer_range_high=float(data["offer_range_high"]),
            confidence=str(data.get("confidence", "medium")),
            reasoning=str(data.get("reasoning", "")),
            market_assessment=str(data.get("market_assessment", "")),
            negotiation_tips=[str(t) for t in data.get("negotiation_tips", [])],
            red_flags=[str(f) for f in data.get("red_flags", [])],
        )
    except Exception as e:
        print(f"[OfferService] AI estimate failed: {e}")
        return None


# --- Orchestrator ---

def get_offer_estimate(listing: Listing) -> OfferEstimate:
    """Fetch comps, run logical CMA, optionally run AI estimate."""
    if not listing.price:
        return OfferEstimate(listing_price=None, error="Listing has no price — cannot estimate offer.")

    comps = fetch_comps(listing)
    logical = calculate_logical_offer(listing, comps)
    ai = calculate_ai_offer(listing, comps, logical) if comps else None

    return OfferEstimate(
        listing_price=listing.price,
        logical=logical,
        ai=ai,
        comps=comps,
        error=None if (logical or ai) else "Not enough comparable sales found in this area.",
    )


# --- Helpers ---

def _safe_float(val) -> Optional[float]:
    try:
        v = float(str(val).replace(",", "").replace("$", "").strip())
        return v if v > 0 else None
    except Exception:
        return None


def _safe_int(val) -> Optional[int]:
    try:
        return int(float(str(val).strip()))
    except Exception:
        return None


def _safe_bool(val) -> Optional[bool]:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).lower().strip()
    if s in ("true", "yes", "1", "y"):
        return True
    if s in ("false", "no", "0", "n", "none", "nan"):
        return False
    return None


def _types_compatible(row_type: str, listing_type: str) -> bool:
    """Check if comp property type is compatible with the listing's type."""
    condo_terms = ("condo", "condominium", "co-op", "coop")
    mf_terms = ("multi", "duplex", "triplex", "fourplex")
    if any(t in listing_type for t in condo_terms):
        return any(t in row_type for t in condo_terms) or row_type == ""
    if any(t in listing_type for t in mf_terms):
        return any(t in row_type for t in mf_terms) or row_type == ""
    # Single family / townhouse — accept if comp is not explicitly condo/multi
    return not any(t in row_type for t in condo_terms + mf_terms)


def _avg_bool(comps: list[ComparableSale], field: str) -> float:
    """Average of a bool field across comps, treating None as unknown (excluded)."""
    values = [getattr(c, field) for c in comps if getattr(c, field) is not None]
    if not values:
        return 0.5  # neutral when unknown
    return sum(1 for v in values if v) / len(values)


def _build_listing_summary(listing: Listing) -> str:
    parts = [
        f"Address: {listing.address}, {listing.city}, {listing.state} {listing.zip_code}",
        f"List price: ${listing.price:,.0f}" if listing.price else "List price: unknown",
        f"Bedrooms: {listing.bedrooms}" if listing.bedrooms else "",
        f"Bathrooms: {listing.bathrooms}" if listing.bathrooms else "",
        f"Sqft: {listing.sqft:,}" if listing.sqft else "",
        f"Lot sqft: {listing.lot_sqft:,}" if listing.lot_sqft else "",
        f"Year built: {listing.year_built}" if listing.year_built else "",
        f"Property type: {listing.property_type}" if listing.property_type else "",
        f"Garage: {'yes' if listing.has_garage else 'no'}" if listing.has_garage is not None else "",
        f"Basement: {'yes' if listing.has_basement else 'no'}" if listing.has_basement is not None else "",
        f"HOA: ${listing.hoa_monthly:.0f}/mo" if listing.hoa_monthly else "",
        f"Days on market: {listing.days_on_mls}" if listing.days_on_mls else "",
    ]
    return "\n".join(p for p in parts if p)


def _build_comp_summary(comps: list[ComparableSale], logical: Optional[LogicalOffer]) -> str:
    if not comps:
        return "No comparable sales found."

    lines = [f"Total comps found: {len(comps)}"]
    if logical:
        lines.append(f"Median price/sqft: ${logical.price_per_sqft_comps:,.2f}")
        lines.append(f"Logical estimated value: ${logical.estimated_value:,}")

    # Show top 5 comps
    for c in comps[:5]:
        price_str = f"${c.price:,.0f}"
        sqft_str = f"{c.sqft:,} sqft" if c.sqft else "sqft unknown"
        ppsf_str = f"${c.price_per_sqft:.0f}/sqft" if c.price_per_sqft else ""
        dom_str = f"{c.days_on_mls}d on market" if c.days_on_mls else ""
        parts = [p for p in [price_str, sqft_str, ppsf_str, dom_str] if p]
        lines.append(f"  - {c.address or 'Unknown'}: {', '.join(parts)}")

    if len(comps) > 5:
        lines.append(f"  ... and {len(comps) - 5} more")

    return "\n".join(lines)
