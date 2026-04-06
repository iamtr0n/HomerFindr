"""Offer estimation service: deep CMA with recency weighting + AI photo analysis."""

from __future__ import annotations

import math
import statistics
import traceback
from datetime import date, datetime
from typing import Optional

from homesearch.models import (
    AIOfferEstimate,
    ComparableSale,
    Listing,
    LogicalOffer,
    OfferEstimate,
)


# --- Comparable listings (recently sold, for the comps page) ---

def get_comparable_listings(listing: Listing, radius_miles: float = 1.5, days_back: int = 180) -> list:
    """Fetch recently sold comparable properties using homeharvest.

    Returns a list of Listing model instances normalized via the same logic
    as HomeHarvestProvider.
    """
    try:
        from homeharvest import scrape_property
        from homesearch.models import Listing as ListingModel

        location = listing.zip_code if listing.zip_code else f"{listing.city}, {listing.state}"
        if not location.strip():
            return []

        try:
            df = scrape_property(location=location, listing_type="sold", past_days=days_back, radius=radius_miles)
        except TypeError:
            # homeharvest version doesn't support radius param
            df = scrape_property(location=location, listing_type="sold", past_days=days_back)

        if df is None or df.empty:
            return []

        results: list[Listing] = []
        for _, row in df.iterrows():
            try:
                sold_price = _safe_float(row.get("sold_price"))
                list_price = _safe_float(row.get("list_price") or row.get("price"))
                price = sold_price or list_price
                if not price or price <= 0:
                    continue

                beds = _safe_int(row.get("beds") or row.get("bedrooms"))
                baths = _safe_float(row.get("full_baths") or row.get("baths") or row.get("bathrooms"))
                sqft = _safe_int(row.get("sqft") or row.get("square_feet"))

                # Bedroom filter: within 1 of target
                if listing.bedrooms and beds and abs(beds - listing.bedrooms) > 1:
                    continue

                # Sqft filter: within 30% of target
                if listing.sqft and sqft:
                    ratio = sqft / listing.sqft
                    if ratio < 0.70 or ratio > 1.30:
                        continue

                street = str(row.get("street") or row.get("address") or "")
                city = str(row.get("city") or listing.city or "")
                state = str(row.get("state") or listing.state or "")
                zip_code = str(row.get("zip_code") or "")
                source_id = str(row.get("mls_id") or row.get("property_url") or f"comp-{street}-{zip_code}")

                desc_lower = str(row.get("description") or row.get("text") or "").lower()
                _pg = row.get("parking_garage")
                has_garage = True if (_pg and str(_pg).lower() not in ("false", "0", "none", "nan")) or "garage" in desc_lower else None
                has_basement = True if "basement" in desc_lower else None

                comp_listing = ListingModel(
                    source="homeharvest_comp",
                    source_id=source_id,
                    address=street,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    price=price,
                    listing_type="sold",
                    property_type=str(row.get("style") or row.get("property_type") or "single_family"),
                    bedrooms=beds,
                    bathrooms=baths,
                    sqft=sqft,
                    lot_sqft=_safe_int(row.get("lot_sqft") or row.get("lot_square_feet")),
                    year_built=_safe_int(row.get("year_built")),
                    has_garage=has_garage,
                    has_basement=has_basement,
                    latitude=_safe_float(row.get("latitude") or row.get("lat")),
                    longitude=_safe_float(row.get("longitude") or row.get("lng") or row.get("lon")),
                    photo_url=str(row.get("primary_photo") or row.get("photo_url") or ""),
                    source_url=str(row.get("property_url") or ""),
                )
                results.append(comp_listing)
            except Exception:
                continue

        return results[:10]

    except Exception:
        traceback.print_exc()
        return []


# --- Comp fetching ---

def fetch_comps(listing: Listing, past_days: int = 365) -> list[ComparableSale]:
    """Fetch recently sold comparable homes.

    Strategy:
    1. Search same ZIP code first (most precise)
    2. If fewer than 5 comps found, also search city+state for more coverage
    3. Filter by property type, beds (±1), baths (±1.5), sqft (±35%)
    4. Assign recency weights (recent = higher weight)
    5. Remove outliers beyond 2 standard deviations from mean $/sqft
    """
    raw: list[ComparableSale] = []

    zip_comps = _fetch_from_location(listing.zip_code, listing, past_days) if listing.zip_code else []
    raw.extend(zip_comps)

    # Expand to city search if fewer than 5 comps
    if len(raw) < 5 and listing.city and listing.state:
        city_location = f"{listing.city}, {listing.state}"
        city_comps = _fetch_from_location(city_location, listing, past_days)
        # Dedupe by address
        seen = {c.address.lower() for c in raw}
        for c in city_comps:
            if c.address.lower() not in seen:
                raw.append(c)
                seen.add(c.address.lower())

    if not raw:
        return []

    # Remove outliers: calc mean + stdev of $/sqft, drop those >2 SD out
    ppsf_vals = [c.price_per_sqft for c in raw if c.price_per_sqft and c.price_per_sqft > 0]
    if len(ppsf_vals) >= 4:
        mean_ppsf = statistics.mean(ppsf_vals)
        stdev_ppsf = statistics.stdev(ppsf_vals)
        cutoff_lo = mean_ppsf - 2 * stdev_ppsf
        cutoff_hi = mean_ppsf + 2 * stdev_ppsf
        raw = [c for c in raw if not c.price_per_sqft or cutoff_lo <= c.price_per_sqft <= cutoff_hi]

    # Sort by recency weight descending, limit to 25 best
    raw.sort(key=lambda c: c.recency_weight, reverse=True)
    return raw[:25]


def _fetch_from_location(location: str, listing: Listing, past_days: int) -> list[ComparableSale]:
    """Inner fetch for a single location string."""
    try:
        from homeharvest import scrape_property

        df = scrape_property(location=location, listing_type="sold", past_days=past_days)
        if df is None or df.empty:
            return []

        today = date.today()
        comps: list[ComparableSale] = []

        for _, row in df.iterrows():
            try:
                sold_price = _safe_float(row.get("sold_price"))
                list_price = _safe_float(row.get("list_price") or row.get("price"))
                price = sold_price or list_price
                if not price or price <= 0:
                    continue

                sqft = _safe_int(row.get("sqft") or row.get("square_feet"))
                lot_sqft = _safe_int(row.get("lot_sqft") or row.get("lot_square_feet"))

                # Property type filter
                row_type = str(row.get("style") or row.get("property_type") or "").lower()
                if not _types_compatible(row_type, (listing.property_type or "single_family").lower()):
                    continue

                # Bedroom filter (±1)
                row_beds = _safe_int(row.get("beds") or row.get("bedrooms"))
                if listing.bedrooms and row_beds and abs(row_beds - listing.bedrooms) > 1:
                    continue

                # Bathroom filter (±1.5)
                row_baths = _safe_float(row.get("full_baths") or row.get("baths") or row.get("bathrooms"))
                if listing.bathrooms and row_baths and abs(row_baths - listing.bathrooms) > 1.5:
                    continue

                # Sqft filter (±35%)
                if listing.sqft and sqft:
                    ratio = sqft / listing.sqft
                    if ratio < 0.65 or ratio > 1.35:
                        continue

                ppsf = round(price / sqft, 2) if sqft and sqft > 0 else None

                # Recency weight
                sold_date_raw = row.get("sold_date") or row.get("close_date")
                days_since = None
                weight = 0.5  # default for unknown date
                if sold_date_raw:
                    try:
                        if hasattr(sold_date_raw, 'date'):
                            sold_dt = sold_date_raw.date()
                        else:
                            sold_dt = datetime.strptime(str(sold_date_raw)[:10], "%Y-%m-%d").date()
                        days_since = (today - sold_dt).days
                        weight = _recency_weight(days_since)
                    except Exception:
                        pass

                # Garage: homeharvest column is parking_garage; fall back to description
                desc_lower = str(row.get("description") or row.get("text") or "").lower()
                _pg = row.get("parking_garage")
                has_garage = True if (_pg and str(_pg).lower() not in ("false", "0", "none", "nan")) or "garage" in desc_lower else None
                has_basement = True if "basement" in desc_lower else None

                comp = ComparableSale(
                    address=str(row.get("street") or row.get("address") or ""),
                    price=price,
                    list_price=list_price,
                    sqft=sqft,
                    lot_sqft=lot_sqft,
                    price_per_sqft=ppsf,
                    bedrooms=row_beds,
                    bathrooms=row_baths,
                    year_built=_safe_int(row.get("year_built")),
                    has_garage=has_garage,
                    has_basement=has_basement,
                    days_on_mls=_safe_int(row.get("days_on_mls") or row.get("days_on_market") or row.get("dom")),
                    days_since_sold=days_since,
                    zip_code=str(row.get("zip_code") or ""),
                    recency_weight=weight,
                )
                comps.append(comp)
            except Exception:
                continue

        return comps

    except Exception:
        traceback.print_exc()
        return []


def _recency_weight(days: int) -> float:
    """Higher weight for more recent sales."""
    if days <= 30:
        return 1.0
    if days <= 60:
        return 0.92
    if days <= 90:
        return 0.85
    if days <= 180:
        return 0.72
    if days <= 270:
        return 0.58
    return 0.45


# --- Logical CMA ---

def calculate_logical_offer(listing: Listing, comps: list[ComparableSale]) -> Optional[LogicalOffer]:
    """Weighted CMA: recency-weighted median $/sqft + feature adjustments + market condition."""
    if not comps or not listing.sqft:
        return None

    valid = [(c.price_per_sqft, c.recency_weight) for c in comps if c.price_per_sqft and c.price_per_sqft > 0]
    if not valid:
        return None

    # Weighted median of $/sqft
    weighted_ppsf = _weighted_median(valid)
    base_value = weighted_ppsf * listing.sqft
    confidence = "high" if len(valid) >= 6 else ("medium" if len(valid) >= 3 else "low")

    # --- Feature adjustments ---
    adjustments: dict[str, float] = {}

    comp_garage_avg = _avg_bool(comps, "has_garage")
    if listing.has_garage is True and comp_garage_avg < 0.4:
        adjustments["garage"] = 14_000.0
    elif listing.has_garage is False and comp_garage_avg >= 0.6:
        adjustments["garage"] = -10_000.0

    comp_basement_avg = _avg_bool(comps, "has_basement")
    if listing.has_basement is True and comp_basement_avg < 0.4:
        adjustments["basement"] = 22_000.0
    elif listing.has_basement is False and comp_basement_avg >= 0.6:
        adjustments["basement"] = -16_000.0

    # Year built — use weighted average of comps
    comp_years = [(c.year_built, c.recency_weight) for c in comps if c.year_built]
    if comp_years and listing.year_built:
        w_avg_year = sum(y * w for y, w in comp_years) / sum(w for _, w in comp_years)
        year_diff = listing.year_built - w_avg_year
        adj = year_diff * 1_500.0  # $1,500 per year newer/older
        if abs(adj) > 1_000:
            adjustments["year_built"] = round(adj, 0)

    # Lot size difference — only when most comps have lot data
    comp_lots = [(c.lot_sqft, c.recency_weight) for c in comps if c.lot_sqft and c.lot_sqft > 0]
    if len(comp_lots) >= 3 and listing.lot_sqft:
        w_avg_lot = sum(ls * w for ls, w in comp_lots) / sum(w for _, w in comp_lots)
        lot_diff = listing.lot_sqft - w_avg_lot
        lot_adj = lot_diff * 2.5  # $2.50/sqft lot diff
        if abs(lot_adj) > 2_000:
            adjustments["lot_size"] = round(lot_adj, 0)

    total_adjustment = sum(adjustments.values())
    estimated_value = base_value + total_adjustment

    # --- Market condition from sold/list ratios (proper weighted average) ---
    overbid_ratio = None
    market_condition = "balanced"
    weighted_ratio_sum = 0.0
    weight_sum = 0.0
    for c in comps:
        if c.list_price and c.list_price > 0 and c.price > 0:
            weighted_ratio_sum += (c.price / c.list_price) * c.recency_weight
            weight_sum += c.recency_weight
    if weight_sum > 0:
        overbid_ratio = round(weighted_ratio_sum / weight_sum, 3)
        if overbid_ratio > 1.03:
            market_condition = "hot"
        elif overbid_ratio < 0.97:
            market_condition = "cool"
        else:
            market_condition = "balanced"

    # Market-adjusted offer tiers
    if market_condition == "hot":
        offer_low = round(estimated_value * 0.99)
        offer_fair = round(estimated_value * 1.02)
        offer_strong = round(estimated_value * 1.05)
    elif market_condition == "cool":
        offer_low = round(estimated_value * 0.92)
        offer_fair = round(estimated_value * 0.96)
        offer_strong = round(estimated_value * 0.99)
    else:
        offer_low = round(estimated_value * 0.95)
        offer_fair = round(estimated_value * 0.985)
        offer_strong = round(estimated_value * 1.01)

    # Listing vs estimate
    listing_price = listing.price or 0
    pct_diff = ((listing_price - estimated_value) / estimated_value * 100) if listing_price > 0 else 0.0
    if pct_diff < -5:
        assessment = "underpriced"
    elif pct_diff > 5:
        assessment = "overpriced"
    else:
        assessment = "fairly_priced"

    # Avg days on market
    dom_vals = [c.days_on_mls for c in comps if c.days_on_mls is not None and c.days_on_mls >= 0]
    avg_dom = round(statistics.mean(dom_vals), 1) if dom_vals else None

    return LogicalOffer(
        estimated_value=round(estimated_value),
        price_per_sqft_comps=round(weighted_ppsf, 2),
        offer_low=offer_low,
        offer_fair=offer_fair,
        offer_strong=offer_strong,
        value_assessment=assessment,
        price_vs_estimate_pct=round(pct_diff, 1),
        comp_count=len(valid),
        confidence=confidence,
        adjustments={k: int(v) for k, v in adjustments.items()},
        market_overbid_ratio=overbid_ratio,
        avg_days_on_market=avg_dom,
        market_condition=market_condition,
    )


# --- AI estimate with photo analysis ---

def _build_ai_prompt(listing_summary: str, comp_summary: str, logical: Optional["LogicalOffer"], has_photo: bool, comps: Optional[list] = None) -> str:
    """Build the shared prompt text used by all AI providers."""
    comps_section = ""
    if comps:
        lines = ["RECENT COMPARABLE SALES:"]
        for c in comps[:8]:
            price_str = f"${c.price:,.0f}" if c.price else "N/A"
            sqft_str = f"{c.sqft:,} sqft" if c.sqft else ""
            ppsf_str = f"${c.price/c.sqft:.0f}/sqft" if c.price and c.sqft else ""
            beds_baths = f"{c.bedrooms}bd/{c.bathrooms}ba" if c.bedrooms and c.bathrooms else ""
            addr = c.address or "Unknown"
            detail = ", ".join(p for p in [price_str, sqft_str, ppsf_str, beds_baths] if p)
            lines.append(f"  • {addr}: {detail}")
        comps_section = "\n".join(lines)

    return f"""You are an expert real estate analyst helping a buyer decide how much to offer on a home.

LISTING DETAILS:
{listing_summary}

COMPARABLE SOLD HOMES (last 12 months, nearby, weighted by recency):
{comp_summary}

{comps_section}

{_market_context(logical)}

{"PHOTO ANALYSIS: Review the listing photo and assess visible condition, style era, and whether the home appears recently renovated. Factor this into your recommendation." if has_photo else ""}

IMPORTANT: In competitive markets, final sale prices routinely exceed asking price. Your estimate should reflect realistic market value, not a conservative floor. If recent comps show a hot market, factor that in.

Provide a JSON response with these exact fields:
{{
  "suggested_offer": <number — single best offer price>,
  "offer_range_low": <number — floor>,
  "offer_range_high": <number — ceiling>,
  "confidence": <"high" | "medium" | "low">,
  "reasoning": <2-3 sentences explaining the offer, referencing comp data and market conditions>,
  "market_assessment": <1 sentence on current market conditions in this area>,
  "condition_assessment": <1 sentence on visible home condition/era from photo, or "Photo not available" if no photo>,
  "negotiation_tips": [<2-3 specific actionable tips as strings>],
  "red_flags": [<any concerns — days on market, price reductions, condition issues, etc. Empty array if none>]
}}

Return only valid JSON, no markdown."""


def _parse_ai_json(text: str) -> Optional[AIOfferEstimate]:
    """Parse JSON from any AI provider's response text into an AIOfferEstimate."""
    import json, re
    text = text.strip()
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    data = json.loads(text)
    return AIOfferEstimate(
        suggested_offer=float(data["suggested_offer"]),
        offer_range_low=float(data["offer_range_low"]),
        offer_range_high=float(data["offer_range_high"]),
        confidence=str(data.get("confidence", "medium")),
        reasoning=str(data.get("reasoning", "")),
        market_assessment=str(data.get("market_assessment", "")),
        condition_assessment=str(data.get("condition_assessment", "")),
        negotiation_tips=[str(t) for t in data.get("negotiation_tips", [])],
        red_flags=[str(f) for f in data.get("red_flags", [])],
    )


def _ai_anthropic(api_key: str, listing: "Listing", prompt_text: str) -> Optional[AIOfferEstimate]:
    """Call Claude (Anthropic) for offer analysis with optional vision."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        content: list = []
        if listing.photo_url:
            try:
                content.append({"type": "image", "source": {"type": "url", "url": listing.photo_url}})
            except Exception:
                pass
        content.append({"type": "text", "text": prompt_text})
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": content}],
        )
        return _parse_ai_json(response.content[0].text)
    except Exception as e:
        print(f"[OfferService] Anthropic failed: {e}")
        return None


def _ai_openai(api_key: str, listing: "Listing", prompt_text: str) -> Optional[AIOfferEstimate]:
    """Call OpenAI GPT-4o for offer analysis with optional vision."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        user_content: list = []
        if listing.photo_url:
            try:
                user_content.append({"type": "image_url", "image_url": {"url": listing.photo_url, "detail": "low"}})
            except Exception:
                pass
        user_content.append({"type": "text", "text": prompt_text})
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=800,
            messages=[{"role": "user", "content": user_content}],
        )
        return _parse_ai_json(response.choices[0].message.content)
    except Exception as e:
        print(f"[OfferService] OpenAI failed: {e}")
        return None


def _ai_google(api_key: str, listing: "Listing", prompt_text: str) -> Optional[AIOfferEstimate]:
    """Call Google Gemini for offer analysis with optional vision."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        parts: list = [prompt_text]
        if listing.photo_url:
            try:
                import requests
                from io import BytesIO
                from PIL import Image
                resp = requests.get(listing.photo_url, timeout=10)
                parts.insert(0, Image.open(BytesIO(resp.content)))
            except Exception:
                pass  # vision unavailable — text-only fallback
        response = model.generate_content(parts)
        return _parse_ai_json(response.text)
    except Exception as e:
        print(f"[OfferService] Google Gemini failed: {e}")
        return None


def calculate_ai_offer(listing: Listing, comps: list[ComparableSale], logical: Optional[LogicalOffer]) -> Optional[AIOfferEstimate]:
    """Multi-provider AI offer analysis: Anthropic → OpenAI → Google (first configured wins)."""
    from homesearch.config import settings

    comparable_listings = get_comparable_listings(listing)
    comp_summary = _build_comp_summary(comps, logical)
    listing_summary = _build_listing_summary(listing)
    prompt_text = _build_ai_prompt(listing_summary, comp_summary, logical, bool(listing.photo_url), comps=comparable_listings)

    if settings.anthropic_api_key:
        result = _ai_anthropic(settings.anthropic_api_key, listing, prompt_text)
        if result:
            return result

    if settings.openai_api_key:
        result = _ai_openai(settings.openai_api_key, listing, prompt_text)
        if result:
            return result

    if settings.google_api_key:
        result = _ai_google(settings.google_api_key, listing, prompt_text)
        if result:
            return result

    return None


# --- Orchestrator ---

def get_offer_estimate(listing: Listing) -> OfferEstimate:
    """Fetch comps, run weighted CMA, optionally run AI estimate."""
    if not listing.price:
        return OfferEstimate(listing_price=None, error="Listing has no price — cannot estimate offer.")

    comps = fetch_comps(listing)
    logical = calculate_logical_offer(listing, comps)
    ai = calculate_ai_offer(listing, comps, logical) if comps else None

    error = None
    if not logical and not ai:
        error = "Not enough comparable sales found in this area to generate an estimate."

    return OfferEstimate(
        listing_price=listing.price,
        logical=logical,
        ai=ai,
        comps=comps,
        error=error,
    )


# --- Helpers ---

def _weighted_median(values_weights: list[tuple[float, float]]) -> float:
    """Compute weighted median of (value, weight) pairs."""
    if not values_weights:
        return 0.0
    # Sort by value, then find the 50th percentile by cumulative weight
    sorted_vw = sorted(values_weights, key=lambda x: x[0])
    total_weight = sum(w for _, w in sorted_vw)
    target = total_weight / 2
    cumulative = 0.0
    for val, weight in sorted_vw:
        cumulative += weight
        if cumulative >= target:
            return val
    return sorted_vw[-1][0]


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
    condo_terms = ("condo", "condominium", "co-op", "coop")
    mf_terms = ("multi", "duplex", "triplex", "fourplex")
    if any(t in listing_type for t in condo_terms):
        return any(t in row_type for t in condo_terms) or row_type == ""
    if any(t in listing_type for t in mf_terms):
        return any(t in row_type for t in mf_terms) or row_type == ""
    return not any(t in row_type for t in condo_terms + mf_terms)


def _avg_bool(comps: list[ComparableSale], field: str) -> float:
    values = [getattr(c, field) for c in comps if getattr(c, field) is not None]
    if not values:
        return 0.5
    return sum(1 for v in values if v) / len(values)


def _market_context(logical: Optional[LogicalOffer]) -> str:
    if not logical:
        return ""
    parts = []
    if logical.market_overbid_ratio is not None:
        pct = (logical.market_overbid_ratio - 1) * 100
        direction = "above" if pct > 0 else "below"
        parts.append(f"Market data: homes in this area sold {abs(pct):.1f}% {direction} list price on average ({logical.market_condition} market).")
    if logical.avg_days_on_market is not None:
        parts.append(f"Average days on market for comps: {logical.avg_days_on_market:.0f} days.")
    return "\n".join(parts)


def _build_listing_summary(listing: Listing) -> str:
    parts = [
        f"Address: {listing.address}, {listing.city}, {listing.state} {listing.zip_code}",
        f"List price: ${listing.price:,.0f}" if listing.price else "",
        f"Bedrooms: {listing.bedrooms}" if listing.bedrooms else "",
        f"Bathrooms: {listing.bathrooms}" if listing.bathrooms else "",
        f"Sqft (living): {listing.sqft:,}" if listing.sqft else "",
        f"Lot sqft: {listing.lot_sqft:,}" if listing.lot_sqft else "",
        f"Year built: {listing.year_built}" if listing.year_built else "",
        f"Property type: {listing.property_type}" if listing.property_type else "",
        f"Garage: {'yes' if listing.has_garage else 'no'}" if listing.has_garage is not None else "",
        f"Basement: {'yes' if listing.has_basement else 'no'}" if listing.has_basement is not None else "",
        f"Pool: yes" if listing.has_pool else "",
        f"Fireplace: yes" if listing.has_fireplace else "",
        f"Central A/C: {'yes' if listing.has_ac else 'no'}" if listing.has_ac is not None else "",
        f"Heat type: {listing.heat_type}" if listing.heat_type else "",
        f"HOA: ${listing.hoa_monthly:.0f}/mo" if listing.hoa_monthly else "",
        f"Days on market: {listing.days_on_mls}" if listing.days_on_mls else "",
        f"Price/sqft: ${listing.price/listing.sqft:.0f}" if listing.price and listing.sqft else "",
    ]
    return "\n".join(p for p in parts if p)


def _build_comp_summary(comps: list[ComparableSale], logical: Optional[LogicalOffer]) -> str:
    if not comps:
        return "No comparable sales found."

    lines = [f"Total comps found: {len(comps)} (after outlier removal and filtering)"]
    if logical:
        lines.append(f"Weighted median price/sqft: ${logical.price_per_sqft_comps:,.2f}")
        lines.append(f"Logical estimated value: ${logical.estimated_value:,}")
        if logical.market_overbid_ratio:
            lines.append(f"Avg sold/list ratio: {logical.market_overbid_ratio:.3f} ({logical.market_condition} market)")
        if logical.avg_days_on_market:
            lines.append(f"Avg days on market: {logical.avg_days_on_market:.0f}")

    lines.append("\nTop comps (most recent first):")
    for c in comps[:8]:
        price_str = f"${c.price:,.0f}"
        sqft_str = f"{c.sqft:,} sqft" if c.sqft else ""
        ppsf_str = f"${c.price_per_sqft:.0f}/sqft" if c.price_per_sqft else ""
        age_str = f"built {c.year_built}" if c.year_built else ""
        recency_str = f"{c.days_since_sold}d ago" if c.days_since_sold else ""
        dom_str = f"{c.days_on_mls}d on mkt" if c.days_on_mls else ""
        detail = ", ".join(p for p in [price_str, sqft_str, ppsf_str, age_str, recency_str, dom_str] if p)
        lines.append(f"  • {c.address or 'Unknown'}: {detail}")

    if len(comps) > 8:
        lines.append(f"  ... and {len(comps) - 8} more")
    return "\n".join(lines)
