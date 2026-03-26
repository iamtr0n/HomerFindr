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

    listing_type: ListingType = ListingType.SALE
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
    year_built: Optional[int] = None
    hoa_monthly: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_url: str = ""
    source_url: str = ""
    match_score: int = 0
    match_badges: list[str] = Field(default_factory=list)
    is_gold_star: bool = False
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


class NotificationSettings(BaseModel):
    """Per-search notification preferences."""

    desktop: bool = True                    # macOS osascript notification
    zapier_webhook: str = ""                # Zapier webhook URL (empty = disabled)
    notify_coming_soon_only: bool = False   # Only alert on coming_soon listing_type


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


class ZipInfo(BaseModel):
    """ZIP code info for the discovery feature."""

    zipcode: str
    city: str
    state: str
    latitude: float
    longitude: float
    population: Optional[int] = None
