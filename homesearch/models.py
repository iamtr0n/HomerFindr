"""Pydantic models for search criteria, listings, and saved searches."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ListingType(str, Enum):
    SALE = "sale"
    RENT = "rent"
    SOLD = "sold"
    COMING_SOON = "coming_soon"
    PENDING = "pending"


class PropertyType(str, Enum):
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi_family"
    COMMERCIAL = "commercial"
    LAND = "land"
    OTHER = "other"


class SearchCriteria(BaseModel):
    """All possible search filters. Every field is optional."""

    location: str = ""  # City, State or ZIP code
    radius_miles: int = 25
    zip_codes: list[str] = Field(default_factory=list)  # Specific ZIPs to include
    excluded_zips: list[str] = Field(default_factory=list)  # ZIPs to skip

    listing_type: ListingType = ListingType.SALE  # kept for backwards compat / single-type searches
    listing_types: list[ListingType] = Field(default_factory=list)  # multi-select; overrides listing_type when set
    property_types: list[PropertyType] = Field(default_factory=list)

    price_min: Optional[int] = None
    price_max: Optional[int] = None

    bedrooms_min: Optional[int] = None
    bathrooms_min: Optional[float] = None

    sqft_min: Optional[int] = None
    sqft_max: Optional[int] = None

    lot_sqft_min: Optional[int] = None
    lot_sqft_max: Optional[int] = None

    year_built_min: Optional[int] = None
    year_built_max: Optional[int] = None

    stories_min: Optional[int] = None

    has_basement: Optional[bool] = None  # None = don't care
    has_garage: Optional[bool] = None
    garage_spaces_min: Optional[int] = None

    hoa_max: Optional[float] = None  # Max monthly HOA

    has_fireplace: Optional[bool] = None
    has_ac: Optional[bool] = None
    heat_type: Optional[str] = None  # "any", "gas", "electric", "radiant", None
    has_pool: Optional[bool] = None

    avoid_highways: bool = False
    school_rating_min: Optional[int] = None  # 1-10

    house_styles: list[str] = Field(default_factory=list)  # e.g. ["cape_cod", "ranch"]
    style_strict: bool = False  # if True, hide listings where style cannot be detected
    days_pending_min: Optional[int] = None  # Only show pending listings with >= this many days on market


class Listing(BaseModel):
    """A normalized property listing from any source."""

    id: Optional[int] = None
    source: str  # "realtor", "redfin", "zillow"
    source_id: str  # Platform-specific ID
    address: str
    city: str = ""
    state: str = ""
    zip_code: str = ""
    price: Optional[float] = None
    listing_type: str = "sale"
    property_type: str = "single_family"
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    lot_sqft: Optional[int] = None
    stories: Optional[int] = None
    has_garage: Optional[bool] = None
    garage_spaces: Optional[int] = None
    has_basement: Optional[bool] = None
    has_fireplace: Optional[bool] = None
    has_ac: Optional[bool] = None
    heat_type: Optional[str] = None  # Detected: "gas", "electric", "radiant", "forced air", etc.
    has_pool: Optional[bool] = None
    near_highway: bool = False
    highway_name: str = ""
    school_rating: Optional[int] = None  # 1-10
    school_district: str = ""
    year_built: Optional[int] = None
    hoa_monthly: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_url: str = ""
    source_url: str = ""
    house_style: Optional[str] = None  # e.g. "cape_cod", "ranch", "colonial"
    match_score: int = 0
    match_badges: list[str] = Field(default_factory=list)
    is_gold_star: bool = False
    is_starred: bool = False  # Starred by a notification alert (tracked across searches)
    is_new: bool = False  # True until the user views the search results
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    days_on_mls: Optional[int] = None
    agent_name: Optional[str] = None
    agent_phone: Optional[str] = None
    agent_email: Optional[str] = None


class NotificationSettings(BaseModel):
    """Per-search notification preferences."""

    desktop: bool = True                    # macOS osascript notification
    zapier_webhook: str = ""                # Zapier webhook URL (empty = disabled)
    notify_coming_soon_only: bool = False   # Only alert on coming_soon listing_type
    alerts_paused: bool = False             # Pause all alerts without deleting settings
    recipients: list[str] = Field(default_factory=list)  # Phone numbers to include in webhook payload


class SavedSearch(BaseModel):
    """A persisted search profile."""

    id: Optional[int] = None
    name: str
    criteria: SearchCriteria
    created_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    is_active: bool = True
    result_count: int = 0
    notification_settings: NotificationSettings = Field(default_factory=NotificationSettings)


class ComparableSale(BaseModel):
    """A sold listing used as a comp for offer estimation."""

    address: str
    price: float
    list_price: Optional[float] = None   # original list price (for sold/list ratio)
    sqft: Optional[int] = None
    lot_sqft: Optional[int] = None
    price_per_sqft: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    year_built: Optional[int] = None
    has_garage: Optional[bool] = None
    has_basement: Optional[bool] = None
    days_on_mls: Optional[int] = None
    days_since_sold: Optional[int] = None  # recency for weighting
    zip_code: str = ""
    recency_weight: float = 1.0  # higher = more recent = more weight


class LogicalOffer(BaseModel):
    """CMA-based offer estimate derived from comparable sales."""

    estimated_value: float
    price_per_sqft_comps: float
    offer_low: float       # conservative
    offer_fair: float      # at or near estimate
    offer_strong: float    # above estimate (competitive market)
    value_assessment: str  # "underpriced", "fairly_priced", "overpriced"
    price_vs_estimate_pct: float  # positive = listing is above estimate
    comp_count: int
    confidence: str        # "high", "medium", "low"
    adjustments: dict      # breakdown of feature adjustments applied
    market_overbid_ratio: Optional[float] = None  # avg sold/list (>1.0 = hot market)
    avg_days_on_market: Optional[float] = None    # how fast comps sold
    market_condition: str = "balanced"            # "hot", "balanced", "cool"


class AIOfferEstimate(BaseModel):
    """Claude-powered offer analysis."""

    suggested_offer: float
    offer_range_low: float
    offer_range_high: float
    confidence: str        # "high", "medium", "low"
    reasoning: str
    market_assessment: str
    condition_assessment: str = ""   # photo-based condition / style era analysis
    negotiation_tips: list[str]
    red_flags: list[str] = Field(default_factory=list)


class OfferEstimate(BaseModel):
    """Combined offer estimate from logical CMA and AI analysis."""

    listing_price: Optional[float]
    logical: Optional[LogicalOffer] = None
    ai: Optional[AIOfferEstimate] = None
    comps: list[ComparableSale] = Field(default_factory=list)
    error: Optional[str] = None


class ZipInfo(BaseModel):
    """ZIP code info for the discovery feature."""

    zipcode: str
    city: str
    state: str
    latitude: float
    longitude: float
    population: Optional[int] = None
    county: Optional[str] = None
