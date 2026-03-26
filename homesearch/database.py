"""SQLite database setup and operations."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from homesearch.config import settings
from homesearch.models import Listing, SavedSearch, SearchCriteria

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    criteria_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_run_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT DEFAULT '',
    state TEXT DEFAULT '',
    zip_code TEXT DEFAULT '',
    price REAL,
    listing_type TEXT DEFAULT 'sale',
    property_type TEXT DEFAULT 'single_family',
    bedrooms INTEGER,
    bathrooms REAL,
    sqft INTEGER,
    lot_sqft INTEGER,
    stories INTEGER,
    has_garage INTEGER,
    garage_spaces INTEGER,
    has_basement INTEGER,
    year_built INTEGER,
    hoa_monthly REAL,
    latitude REAL,
    longitude REAL,
    photo_url TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS search_results (
    search_id INTEGER NOT NULL,
    listing_id INTEGER NOT NULL,
    found_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_new INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (search_id, listing_id),
    FOREIGN KEY (search_id) REFERENCES saved_searches(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_listings_zip ON listings(zip_code);
CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source, source_id);
CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price);
"""


def get_db_path() -> str:
    return settings.database_path


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    # Add new filter columns (safe — ALTER TABLE ADD COLUMN is idempotent when wrapped in try/except)
    for col, col_type in [
        ("has_fireplace", "INTEGER"),
        ("has_ac", "INTEGER"),
        ("heat_type", "TEXT"),
        ("has_pool", "INTEGER"),
    ]:
        try:
            conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {col_type}")
            conn.commit()
        except Exception:
            pass  # Column already exists
    conn.close()


# --- Saved Searches ---

def save_search(search: SavedSearch) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO saved_searches (name, criteria_json, is_active) VALUES (?, ?, ?)",
            (search.name, search.criteria.model_dump_json(), int(search.is_active)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_saved_searches(active_only: bool = False) -> list[SavedSearch]:
    conn = get_connection()
    try:
        query = """
            SELECT ss.*,
                   COALESCE((
                       SELECT COUNT(*)
                       FROM search_results sr
                       WHERE sr.search_id = ss.id
                   ), 0) AS result_count
            FROM saved_searches ss
        """
        if active_only:
            query += " WHERE ss.is_active = 1"
        query += " ORDER BY ss.created_at DESC"
        rows = conn.execute(query).fetchall()
        results = []
        for row in rows:
            results.append(SavedSearch(
                id=row["id"],
                name=row["name"],
                criteria=SearchCriteria.model_validate_json(row["criteria_json"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
                is_active=bool(row["is_active"]),
                result_count=row["result_count"],
            ))
        return results
    finally:
        conn.close()


def get_saved_search(search_id: int) -> Optional[SavedSearch]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT ss.*,
                   COALESCE((
                       SELECT COUNT(*)
                       FROM search_results sr
                       WHERE sr.search_id = ss.id
                   ), 0) AS result_count
            FROM saved_searches ss
            WHERE ss.id = ?
            """,
            (search_id,),
        ).fetchone()
        if not row:
            return None
        return SavedSearch(
            id=row["id"],
            name=row["name"],
            criteria=SearchCriteria.model_validate_json(row["criteria_json"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
            is_active=bool(row["is_active"]),
            result_count=row["result_count"],
        )
    finally:
        conn.close()


def get_saved_search_by_name(name: str) -> Optional[SavedSearch]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT ss.*,
                   COALESCE((
                       SELECT COUNT(*)
                       FROM search_results sr
                       WHERE sr.search_id = ss.id
                   ), 0) AS result_count
            FROM saved_searches ss
            WHERE ss.name = ?
            """,
            (name,),
        ).fetchone()
        if not row:
            return None
        return SavedSearch(
            id=row["id"],
            name=row["name"],
            criteria=SearchCriteria.model_validate_json(row["criteria_json"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
            is_active=bool(row["is_active"]),
            result_count=row["result_count"],
        )
    finally:
        conn.close()


def update_search(search_id: int, **kwargs):
    conn = get_connection()
    try:
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k == "criteria":
                sets.append("criteria_json = ?")
                vals.append(v.model_dump_json() if hasattr(v, "model_dump_json") else json.dumps(v))
            elif k == "is_active":
                sets.append("is_active = ?")
                vals.append(int(v))
            else:
                sets.append(f"{k} = ?")
                vals.append(v)
        vals.append(search_id)
        conn.execute(f"UPDATE saved_searches SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    finally:
        conn.close()


def delete_search(search_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
        conn.commit()
    finally:
        conn.close()


# --- Listings ---

def upsert_listing(listing: Listing) -> int:
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM listings WHERE source = ? AND source_id = ?",
            (listing.source, listing.source_id),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE listings SET price=?, last_seen_at=datetime('now'), photo_url=?, source_url=? WHERE id=?",
                (listing.price, listing.photo_url, listing.source_url, existing["id"]),
            )
            conn.commit()
            return existing["id"]

        cursor = conn.execute(
            """INSERT INTO listings (
                source, source_id, address, city, state, zip_code, price,
                listing_type, property_type, bedrooms, bathrooms, sqft, lot_sqft,
                stories, has_garage, garage_spaces, has_basement, has_fireplace,
                has_ac, heat_type, has_pool, year_built,
                hoa_monthly, latitude, longitude, photo_url, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                listing.source, listing.source_id, listing.address, listing.city,
                listing.state, listing.zip_code, listing.price, listing.listing_type,
                listing.property_type, listing.bedrooms, listing.bathrooms,
                listing.sqft, listing.lot_sqft, listing.stories,
                int(listing.has_garage) if listing.has_garage is not None else None,
                listing.garage_spaces,
                int(listing.has_basement) if listing.has_basement is not None else None,
                int(listing.has_fireplace) if listing.has_fireplace is not None else None,
                int(listing.has_ac) if listing.has_ac is not None else None,
                listing.heat_type,
                int(listing.has_pool) if listing.has_pool is not None else None,
                listing.year_built, listing.hoa_monthly, listing.latitude,
                listing.longitude, listing.photo_url, listing.source_url,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def link_search_result(search_id: int, listing_id: int, is_new: bool = True):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO search_results (search_id, listing_id, is_new) VALUES (?, ?, ?)",
            (search_id, listing_id, int(is_new)),
        )
        conn.commit()
    finally:
        conn.close()


def get_search_results(search_id: int, new_only: bool = False) -> list[Listing]:
    conn = get_connection()
    try:
        query = """
            SELECT l.*, sr.is_new, sr.found_at
            FROM listings l
            JOIN search_results sr ON l.id = sr.listing_id
            WHERE sr.search_id = ?
        """
        if new_only:
            query += " AND sr.is_new = 1"
        query += " ORDER BY sr.found_at DESC"
        rows = conn.execute(query, (search_id,)).fetchall()
        return [_row_to_listing(row) for row in rows]
    finally:
        conn.close()


def get_previous_listing_ids(search_id: int) -> set[int]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT listing_id FROM search_results WHERE search_id = ?", (search_id,)
        ).fetchall()
        return {row["listing_id"] for row in rows}
    finally:
        conn.close()


def mark_results_not_new(search_id: int):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE search_results SET is_new = 0 WHERE search_id = ?", (search_id,)
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_listing(row) -> Listing:
    return Listing(
        id=row["id"],
        source=row["source"],
        source_id=row["source_id"],
        address=row["address"],
        city=row["city"],
        state=row["state"],
        zip_code=row["zip_code"],
        price=row["price"],
        listing_type=row["listing_type"],
        property_type=row["property_type"],
        bedrooms=row["bedrooms"],
        bathrooms=row["bathrooms"],
        sqft=row["sqft"],
        lot_sqft=row["lot_sqft"],
        stories=row["stories"],
        has_garage=bool(row["has_garage"]) if row["has_garage"] is not None else None,
        garage_spaces=row["garage_spaces"],
        has_basement=bool(row["has_basement"]) if row["has_basement"] is not None else None,
        has_fireplace=bool(row["has_fireplace"]) if row["has_fireplace"] is not None else None,
        has_ac=bool(row["has_ac"]) if row["has_ac"] is not None else None,
        heat_type=row["heat_type"],
        has_pool=bool(row["has_pool"]) if row["has_pool"] is not None else None,
        year_built=row["year_built"],
        hoa_monthly=row["hoa_monthly"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        photo_url=row["photo_url"],
        source_url=row["source_url"],
        first_seen_at=datetime.fromisoformat(row["first_seen_at"]) if row["first_seen_at"] else None,
        last_seen_at=datetime.fromisoformat(row["last_seen_at"]) if row["last_seen_at"] else None,
    )
