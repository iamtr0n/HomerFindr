"""SQLite database setup and operations."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from homesearch.config import settings
from homesearch.models import Listing, NotificationSettings, SavedSearch, SearchCriteria

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

CREATE TABLE IF NOT EXISTS viewed_listings (
    source_id TEXT PRIMARY KEY,
    viewed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pending_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id INTEGER,
    search_name TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    attempts INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS listing_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    old_price REAL,
    new_price REAL,
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_price_history_listing ON listing_price_history(listing_id, changed_at DESC);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dismissed_listings (
    source_id TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT 'default',
    dismissed_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source_id, session_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS starred_listings (
    listing_id INTEGER NOT NULL,
    session_id TEXT NOT NULL DEFAULT 'default',
    starred_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (listing_id, session_id),
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);
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
    # Add notification_settings_json column to saved_searches
    try:
        conn.execute("ALTER TABLE saved_searches ADD COLUMN notification_settings_json TEXT DEFAULT '{}'")
        conn.commit()
    except Exception:
        pass  # Column already exists
    # Add is_starred column to listings (marks listings that triggered an alert)
    try:
        conn.execute("ALTER TABLE listings ADD COLUMN is_starred INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # Column already exists
    # Add session_id to saved_searches
    try:
        conn.execute("ALTER TABLE saved_searches ADD COLUMN session_id TEXT DEFAULT 'default'")
        conn.commit()
    except Exception:
        pass
    # Ensure sessions table exists (idempotent)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS dismissed_listings (
            source_id TEXT NOT NULL,
            session_id TEXT NOT NULL DEFAULT 'default',
            dismissed_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (source_id, session_id)
        );
    """)
    conn.commit()
    # Create price history table for existing databases
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS listing_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            old_price REAL,
            new_price REAL,
            changed_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_price_history_listing ON listing_price_history(listing_id, changed_at DESC);
    """)
    # Add days_on_mls column
    try:
        conn.execute("ALTER TABLE listings ADD COLUMN days_on_mls INTEGER")
        conn.commit()
    except Exception:
        pass
    # Migrate legacy is_starred=1 rows into the starred_listings join table
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS starred_listings (
            listing_id INTEGER NOT NULL,
            session_id TEXT NOT NULL DEFAULT 'default',
            starred_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (listing_id, session_id),
            FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
        );
        INSERT OR IGNORE INTO starred_listings (listing_id, session_id)
            SELECT id, 'default' FROM listings WHERE is_starred = 1;
    """)
    conn.commit()
    conn.close()


# --- Saved Searches ---

def save_search(search: SavedSearch, session_id: str = "default") -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO saved_searches (name, criteria_json, is_active, session_id) VALUES (?, ?, ?, ?)",
            (search.name, search.criteria.model_dump_json(), int(search.is_active), session_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_saved_searches(active_only: bool = False, session_id: Optional[str] = None) -> list[SavedSearch]:
    conn = get_connection()
    try:
        conditions = []
        params = []
        if active_only:
            conditions.append("ss.is_active = 1")
        if session_id is not None:
            conditions.append("ss.session_id = ?")
            params.append(session_id)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        query = f"""
            SELECT ss.*,
                   COALESCE((
                       SELECT COUNT(*)
                       FROM search_results sr
                       WHERE sr.search_id = ss.id
                   ), 0) AS result_count
            FROM saved_searches ss
            {where}
            ORDER BY ss.created_at DESC
        """
        rows = conn.execute(query, params).fetchall()
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
                notification_settings=NotificationSettings.model_validate_json(
                    row["notification_settings_json"] or "{}"
                ),
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
            notification_settings=NotificationSettings.model_validate_json(
                row["notification_settings_json"] or "{}"
            ),
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
            notification_settings=NotificationSettings.model_validate_json(
                row["notification_settings_json"] or "{}"
            ),
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
            elif k == "notification_settings":
                sets.append("notification_settings_json = ?")
                vals.append(v.model_dump_json() if hasattr(v, "model_dump_json") else json.dumps(v))
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

def upsert_listing(listing: Listing) -> tuple[int, Optional[str], Optional[float]]:
    """Insert or update a listing. Returns (listing_id, previous_listing_type, previous_price).
    previous_listing_type and previous_price are None for new listings, or the old values
    when the listing already existed (useful for detecting status changes and price drops).
    """
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id, listing_type, price FROM listings WHERE source = ? AND source_id = ?",
            (listing.source, listing.source_id),
        ).fetchone()

        if existing:
            prev_type = existing["listing_type"]
            prev_price = existing["price"]
            conn.execute(
                """UPDATE listings SET
                    price=?, listing_type=?, last_seen_at=datetime('now'),
                    photo_url=?, source_url=?, days_on_mls=?,
                    bedrooms=COALESCE(?, bedrooms), bathrooms=COALESCE(?, bathrooms),
                    sqft=COALESCE(?, sqft), lot_sqft=COALESCE(?, lot_sqft),
                    year_built=COALESCE(?, year_built),
                    has_garage=COALESCE(?, has_garage), has_basement=COALESCE(?, has_basement),
                    latitude=COALESCE(?, latitude), longitude=COALESCE(?, longitude)
                WHERE id=?""",
                (
                    listing.price, listing.listing_type, listing.photo_url,
                    listing.source_url, listing.days_on_mls,
                    listing.bedrooms, listing.bathrooms, listing.sqft, listing.lot_sqft,
                    listing.year_built,
                    int(listing.has_garage) if listing.has_garage is not None else None,
                    int(listing.has_basement) if listing.has_basement is not None else None,
                    listing.latitude, listing.longitude,
                    existing["id"],
                ),
            )
            conn.commit()
            return existing["id"], prev_type, prev_price

        cursor = conn.execute(
            """INSERT INTO listings (
                source, source_id, address, city, state, zip_code, price,
                listing_type, property_type, bedrooms, bathrooms, sqft, lot_sqft,
                stories, has_garage, garage_spaces, has_basement, has_fireplace,
                has_ac, heat_type, has_pool, year_built,
                hoa_monthly, latitude, longitude, photo_url, source_url, days_on_mls
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                listing.longitude, listing.photo_url, listing.source_url, listing.days_on_mls,
            ),
        )
        conn.commit()
        return cursor.lastrowid, None, None
    finally:
        conn.close()


def record_price_change(listing_id: int, old_price: Optional[float], new_price: Optional[float]) -> None:
    """Record a price change for a listing."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO listing_price_history (listing_id, old_price, new_price) VALUES (?, ?, ?)",
            (listing_id, old_price, new_price),
        )
        conn.commit()
    finally:
        conn.close()


def get_price_changes_for_listings(listing_ids: list[int]) -> dict[int, dict]:
    """Return the most recent price change for each listing_id. Keys are listing IDs."""
    if not listing_ids:
        return {}
    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(listing_ids))
        rows = conn.execute(
            f"""
            SELECT ph.listing_id, ph.old_price, ph.new_price, ph.changed_at
            FROM listing_price_history ph
            INNER JOIN (
                SELECT listing_id, MAX(changed_at) AS max_at
                FROM listing_price_history
                WHERE listing_id IN ({placeholders})
                GROUP BY listing_id
            ) latest ON ph.listing_id = latest.listing_id AND ph.changed_at = latest.max_at
            """,
            listing_ids,
        ).fetchall()
        result = {}
        for row in rows:
            old_p = row["old_price"]
            new_p = row["new_price"]
            delta = None
            delta_pct = None
            if old_p and new_p and old_p > 0:
                delta = new_p - old_p
                delta_pct = round((delta / old_p) * 100, 1)
            result[row["listing_id"]] = {
                "old_price": old_p,
                "new_price": new_p,
                "delta": delta,
                "delta_pct": delta_pct,
                "changed_at": row["changed_at"],
            }
        return result
    finally:
        conn.close()


def mark_viewed(source_id: str) -> None:
    """Record that a listing was opened in the browser."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO viewed_listings (source_id, viewed_at) VALUES (?, datetime('now'))",
            (source_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_viewed_source_ids(source_ids: list[str]) -> set[str]:
    """Return the subset of source_ids that have been viewed."""
    if not source_ids:
        return set()
    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(source_ids))
        rows = conn.execute(
            f"SELECT source_id FROM viewed_listings WHERE source_id IN ({placeholders})",
            source_ids,
        ).fetchall()
        return {row["source_id"] for row in rows}
    finally:
        conn.close()


def mark_listing_starred(listing_id: int) -> None:
    """Mark a listing as starred (triggered an alert notification)."""
    conn = get_connection()
    try:
        conn.execute("UPDATE listings SET is_starred = 1 WHERE id = ?", (listing_id,))
        conn.commit()
    finally:
        conn.close()


def toggle_listing_starred(listing_id: int, session_id: str = "default") -> bool:
    """Toggle the starred/saved state of a listing for a session. Returns the new state."""
    conn = get_connection()
    try:
        exists = conn.execute(
            "SELECT 1 FROM starred_listings WHERE listing_id = ? AND session_id = ?",
            (listing_id, session_id),
        ).fetchone()
        if exists:
            conn.execute(
                "DELETE FROM starred_listings WHERE listing_id = ? AND session_id = ?",
                (listing_id, session_id),
            )
            conn.commit()
            return False
        else:
            conn.execute(
                "INSERT OR IGNORE INTO starred_listings (listing_id, session_id) VALUES (?, ?)",
                (listing_id, session_id),
            )
            conn.commit()
            return True
    finally:
        conn.close()


def get_listing_by_id(listing_id: int) -> Optional[Listing]:
    """Fetch a single listing by its database primary key."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)
        ).fetchone()
        if not row:
            return None
        return _row_to_listing(row)
    finally:
        conn.close()


def get_all_listings() -> list[Listing]:
    """Return all listings across every search, deduplicated, newest first.

    is_new is 1 if the listing is new in any saved search (not yet seen).
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.*, MAX(sr.is_new) AS is_new
            FROM listings l
            JOIN search_results sr ON l.id = sr.listing_id
            GROUP BY l.id
            ORDER BY l.last_seen_at DESC
            """
        ).fetchall()
        return [_row_to_listing(row) for row in rows]
    finally:
        conn.close()


def get_starred_listings(session_id: str = "default") -> list[Listing]:
    """Return user-saved listings for a session, most recently starred first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.*, sl.starred_at,
                   1 AS is_starred,
                   COALESCE(MAX(sr.is_new), 0) AS is_new
            FROM listings l
            JOIN starred_listings sl ON l.id = sl.listing_id AND sl.session_id = ?
            LEFT JOIN search_results sr ON l.id = sr.listing_id
            GROUP BY l.id
            ORDER BY sl.starred_at DESC
            """,
            (session_id,),
        ).fetchall()
        return [_row_to_listing(row) for row in rows]
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


def get_seen_listing_ids(search_id: int) -> set[int]:
    """Return only listing IDs that have already been alerted (is_new=0).

    Used by the scheduler to detect listings found by manual runs that
    were never alerted — those have is_new=1 and won't appear here.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT listing_id FROM search_results WHERE search_id = ? AND is_new = 0",
            (search_id,),
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


def mark_listings_alerted(listing_ids: list[int]) -> None:
    """Mark specific listings as seen (is_new=0) across ALL searches.

    Prevents duplicate alerts when the same listing appears in multiple
    saved searches — once alerted for any search, it won't fire again.
    """
    if not listing_ids:
        return
    conn = get_connection()
    try:
        placeholders = ",".join("?" * len(listing_ids))
        conn.execute(
            f"UPDATE search_results SET is_new = 0 WHERE listing_id IN ({placeholders})",
            listing_ids,
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
        days_on_mls=row["days_on_mls"] if "days_on_mls" in row.keys() else None,
        first_seen_at=datetime.fromisoformat(row["first_seen_at"]) if row["first_seen_at"] else None,
        last_seen_at=datetime.fromisoformat(row["last_seen_at"]) if row["last_seen_at"] else None,
        is_starred=bool(row["is_starred"]) if "is_starred" in row.keys() and row["is_starred"] else False,
        is_new=bool(row["is_new"]) if "is_new" in row.keys() and row["is_new"] else False,
    )


# --- Alert Queue ---

def queue_alert(search_id: Optional[int], search_name: str, webhook_url: str, payload: dict) -> int:
    """Save a failed webhook alert for later retry."""
    import json
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO pending_alerts (search_id, search_name, webhook_url, payload_json) VALUES (?, ?, ?, ?)",
            (search_id, search_name, webhook_url, json.dumps(payload)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_pending_alerts() -> list[dict]:
    """Return all unsent alerts, oldest first."""
    import json
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, search_id, search_name, webhook_url, payload_json, attempts FROM pending_alerts ORDER BY created_at ASC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "search_id": r["search_id"],
                "search_name": r["search_name"],
                "webhook_url": r["webhook_url"],
                "payload": json.loads(r["payload_json"]),
                "attempts": r["attempts"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def mark_alert_sent(alert_id: int) -> None:
    """Remove a successfully delivered alert from the queue."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM pending_alerts WHERE id = ?", (alert_id,))
        conn.commit()
    finally:
        conn.close()


def increment_alert_attempts(alert_id: int) -> None:
    """Bump the attempt counter on a failed retry."""
    conn = get_connection()
    try:
        conn.execute("UPDATE pending_alerts SET attempts = attempts + 1 WHERE id = ?", (alert_id,))
        conn.commit()
    finally:
        conn.close()


def get_new_listing_counts_per_search() -> dict[int, int]:
    """Return {search_id: new_listing_count} for all searches that have unseen listings."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT search_id, COUNT(*) AS cnt FROM search_results WHERE is_new = 1 GROUP BY search_id"
        ).fetchall()
        return {row["search_id"]: row["cnt"] for row in rows}
    finally:
        conn.close()


# --- Push subscriptions ---

def save_push_subscription(sub_id: str, endpoint: str, p256dh: str, auth: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO push_subscriptions (id, endpoint, p256dh, auth) VALUES (?, ?, ?, ?)",
            (sub_id, endpoint, p256dh, auth),
        )
        conn.commit()
    finally:
        conn.close()


def delete_push_subscription(sub_id: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM push_subscriptions WHERE id = ?", (sub_id,))
        conn.commit()
    finally:
        conn.close()


def get_all_push_subscriptions() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, endpoint, p256dh, auth FROM push_subscriptions").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Sessions ---

def create_session(session_id: str) -> bool:
    """Insert session. Returns True if it was newly created, False if it already existed."""
    conn = get_connection()
    try:
        cursor = conn.execute("INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def migrate_default_to_session(session_id: str) -> None:
    """One-time migration: move all 'default' searches and dismissals to a real session.
    Called when a brand-new session is first created so existing data is not lost."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE saved_searches SET session_id = ? WHERE session_id = 'default'",
            (session_id,),
        )
        conn.execute(
            """INSERT OR IGNORE INTO dismissed_listings (source_id, session_id, dismissed_at)
               SELECT source_id, ?, dismissed_at FROM dismissed_listings WHERE session_id = 'default'""",
            (session_id,),
        )
        conn.execute("DELETE FROM dismissed_listings WHERE session_id = 'default'")
        conn.commit()
    finally:
        conn.close()


# --- Dismissed listings ---

def dismiss_listing(source_id: str, session_id: str = "default") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO dismissed_listings (source_id, session_id) VALUES (?, ?)",
            (source_id, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def undismiss_listing(source_id: str, session_id: str = "default") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM dismissed_listings WHERE source_id = ? AND session_id = ?",
            (source_id, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_dismissed_source_ids(session_id: str = "default") -> set[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT source_id FROM dismissed_listings WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        return {row["source_id"] for row in rows}
    finally:
        conn.close()
