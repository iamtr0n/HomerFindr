"""FastAPI REST API for the web frontend."""

import asyncio
import json
import random
import string
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from homesearch import database as db
from homesearch.config import settings
from homesearch.models import Listing, NotificationSettings, SavedSearch, SearchCriteria
from homesearch.services.search_service import run_search
from homesearch.services.zip_service import discover_zip_codes
from homesearch.models import ZipInfo


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.init_db()
    yield
    # Shutdown (Phase 2 will add stop_scheduler here)


app = FastAPI(title="HomeSearch API", version="0.1.0", lifespan=lifespan)

# Only allow requests from private/loopback IPs — blocks external internet access
_PRIVATE_PREFIXES = ("127.", "10.", "::1", "localhost")
_PRIVATE_172 = tuple(f"172.{i}." for i in range(16, 32))

@app.middleware("http")
async def lan_only(request: Request, call_next):
    client_ip = request.client.host if request.client else ""
    if (
        any(client_ip.startswith(p) for p in _PRIVATE_PREFIXES)
        or any(client_ip.startswith(p) for p in _PRIVATE_172)
        or client_ip.startswith("192.168.")
    ):
        return await call_next(request)
    return JSONResponse({"detail": "Access restricted to local network."}, status_code=403)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Search endpoints ---

class SearchRequest(BaseModel):
    criteria: SearchCriteria
    save_as: Optional[str] = None


class SearchResponse(BaseModel):
    results: list[Listing]
    total: int
    search_id: Optional[int] = None
    search_name: Optional[str] = None
    provider_errors: list[str] = []


@app.get("/api/version")
def get_version():
    """Return the running package version."""
    try:
        from importlib.metadata import version as pkg_version
        v = pkg_version("homesearch")
    except Exception:
        v = "dev"
    return {"version": v}


@app.post("/api/search/preview", response_model=SearchResponse)
def preview_search(req: SearchRequest):
    """Run a search without saving it."""
    provider_errors: list[str] = []
    results = run_search(req.criteria, errors=provider_errors)
    return SearchResponse(results=results, total=len(results),
                          provider_errors=provider_errors)


@app.post("/api/search/stream")
async def stream_search(req: SearchRequest, request: Request):
    """Run a search with SSE progress streaming."""
    session_id = _get_session(request)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    # Save the search before streaming if a name was provided
    search_id: Optional[int] = None
    search_name: Optional[str] = None
    if req.save_as:
        search_name = req.save_as
        saved = SavedSearch(name=search_name, criteria=req.criteria)
        search_id = db.save_search(saved, session_id=session_id)

    def on_progress(current: int, total: int, location: str, found: int = 0):
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"type": "progress", "current": current, "total": total, "location": location}
        )

    def on_partial(batch: list):
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"type": "partial", "listings": [r.model_dump() for r in batch]}
        )

    def run_in_thread():
        provider_errors: list[str] = []
        results = run_search(
            req.criteria,
            search_id=search_id,
            errors=provider_errors,
            on_progress=on_progress,
            on_partial=on_partial,
        )
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "results",
                "results": [r.model_dump() for r in results],
                "total": len(results),
                "search_id": search_id,
                "search_name": search_name,
                "provider_errors": provider_errors,
            }
        )

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()

    async def event_generator():
        while True:
            msg = await queue.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["type"] == "results":
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/searches", response_model=SearchResponse)
def create_and_run_search(req: SearchRequest, request: Request):
    """Create a saved search and run it immediately."""
    session_id = _get_session(request)
    name = req.save_as or f"Search {req.criteria.location}"
    saved = SavedSearch(name=name, criteria=req.criteria)
    search_id = db.save_search(saved, session_id=session_id)
    provider_errors: list[str] = []
    results = run_search(req.criteria, search_id=search_id, errors=provider_errors)
    return SearchResponse(
        results=results, total=len(results),
        search_id=search_id, search_name=name,
        provider_errors=provider_errors,
    )


@app.get("/api/searches")
def list_searches(request: Request):
    """List all saved searches with unseen listing counts."""
    session_id = _get_session(request)
    searches = db.get_saved_searches(session_id=session_id)
    new_counts = db.get_new_listing_counts_per_search()
    result = []
    for s in searches:
        d = s.model_dump()
        d["new_count"] = new_counts.get(s.id, 0)
        result.append(d)
    return {"searches": result}


@app.get("/api/searches/{search_id}")
def get_search(search_id: int):
    """Get a saved search by ID."""
    search = db.get_saved_search(search_id)
    if not search:
        raise HTTPException(404, "Search not found")
    return search.model_dump()


@app.put("/api/searches/{search_id}")
def update_search(search_id: int, req: SearchRequest):
    """Update a saved search."""
    existing = db.get_saved_search(search_id)
    if not existing:
        raise HTTPException(404, "Search not found")
    updates = {"criteria": req.criteria}
    if req.save_as:
        updates["name"] = req.save_as
    db.update_search(search_id, **updates)
    return {"status": "updated"}


@app.patch("/api/searches/{search_id}/active")
def toggle_search_active(search_id: int, body: dict):
    """Enable or disable a saved search (sets is_active)."""
    existing = db.get_saved_search(search_id)
    if not existing:
        raise HTTPException(404, "Search not found")
    db.update_search(search_id, is_active=bool(body.get("is_active", True)))
    return {"status": "updated"}


@app.delete("/api/searches/{search_id}")
def delete_search(search_id: int):
    """Delete a saved search."""
    existing = db.get_saved_search(search_id)
    if not existing:
        raise HTTPException(404, "Search not found")
    db.delete_search(search_id)
    return {"status": "deleted"}


@app.post("/api/searches/{search_id}/run", response_model=SearchResponse)
def run_saved_search(search_id: int):
    """Re-run a saved search."""
    search = db.get_saved_search(search_id)
    if not search:
        raise HTTPException(404, "Search not found")
    provider_errors: list[str] = []
    results = run_search(search.criteria, search_id=search_id, errors=provider_errors)
    return SearchResponse(
        results=results, total=len(results),
        search_id=search_id, search_name=search.name,
        provider_errors=provider_errors,
    )


@app.get("/api/searches/{search_id}/results")
def get_search_results(request: Request, search_id: int, new_only: bool = False):
    """Get cached results for a saved search, excluding dismissed listings."""
    search = db.get_saved_search(search_id)
    if not search:
        raise HTTPException(404, "Search not found")
    session_id = _get_session(request)
    dismissed = db.get_dismissed_source_ids(session_id=session_id)
    results = db.get_search_results(search_id, new_only=new_only)
    listing_ids = [r.id for r in results if r.id]
    price_changes = db.get_price_changes_for_listings(listing_ids)
    listings_out = []
    for r in results:
        if r.source_id in dismissed:
            continue
        d = r.model_dump()
        d["price_change"] = price_changes.get(r.id)
        listings_out.append(d)
    return {"results": listings_out, "total": len(listings_out)}


# --- ZIP discovery ---

@app.get("/api/zips/discover")
def discover_zips(location: str, radius: int = 25):
    """Discover ZIP codes for a location + radius."""
    zips = discover_zip_codes(location, radius)
    return {"zips": [z.model_dump() for z in zips], "total": len(zips)}


# --- Report ---

@app.post("/api/report/generate")
def generate_report_endpoint():
    """Generate and return the report data (without emailing)."""
    from homesearch.services.report_service import generate_report
    data = generate_report()
    result = {}
    for name, d in data.items():
        result[name] = {
            "new_count": len(d["new_listings"]),
            "total": d["total"],
            "new_listings": [l.model_dump() for l in d["new_listings"]],
        }
    return result


@app.post("/api/report/send")
def send_report_endpoint():
    """Generate and send the email report."""
    from homesearch.services.report_service import generate_report, send_email_report
    data = generate_report()
    success = send_email_report(data)
    return {"sent": success}


# --- Settings status ---

def _env_file_path() -> Path:
    """Locate or create the .env file the server reads from."""
    cwd_env = Path(".env")
    if cwd_env.exists():
        return cwd_env
    home_env = Path.home() / ".homesearch" / ".env"
    home_env.parent.mkdir(parents=True, exist_ok=True)
    home_env.touch()
    return home_env


@app.get("/api/settings/status")
def get_settings_status():
    """Return which optional features are configured."""
    smtp_ok = bool(settings.smtp_user and settings.smtp_password and settings.report_email)
    return {
        "smtp_configured": smtp_ok,
        "report_email": settings.report_email if smtp_ok else "",
    }


async def _geocode_address(address: str) -> tuple[float, float] | None:
    """Geocode an address using Nominatim (OpenStreetMap). Returns (lat, lng) or None."""
    import httpx
    try:
        resp = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "HomerFindr/1.0"},
            timeout=10,
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None


@app.get("/api/settings")
def get_all_settings():
    """Return all configurable settings (passwords masked)."""
    return {
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user,
        "smtp_password_set": bool(settings.smtp_password),
        "report_email": settings.report_email,
        "report_hour": settings.report_hour,
        "report_minute": settings.report_minute,
        "zapier_webhook_url": settings.zapier_webhook_url,
        "env_file": str(_env_file_path()),
        "work_address": settings.work_address,
        "work_lat": settings.work_lat,
        "work_lng": settings.work_lng,
        # AI — never return keys, only whether each provider is configured
        "anthropic_api_key_set": bool(settings.anthropic_api_key),
        "openai_api_key_set": bool(settings.openai_api_key),
        "google_api_key_set": bool(settings.google_api_key),
    }


class SettingsUpdateRequest(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    report_email: Optional[str] = None
    report_hour: Optional[int] = None
    report_minute: Optional[int] = None
    zapier_webhook_url: Optional[str] = None
    work_address: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None


@app.put("/api/settings")
def update_all_settings(req: SettingsUpdateRequest):
    """Write changed settings to .env and update in-memory config."""
    try:
        from dotenv import set_key
    except ImportError:
        raise HTTPException(500, "python-dotenv not available")

    env_file = _env_file_path()
    field_map = {
        "smtp_host": "SMTP_HOST",
        "smtp_port": "SMTP_PORT",
        "smtp_user": "SMTP_USER",
        "smtp_password": "SMTP_PASSWORD",
        "report_email": "REPORT_EMAIL",
        "report_hour": "REPORT_HOUR",
        "report_minute": "REPORT_MINUTE",
        "zapier_webhook_url": "ZAPIER_WEBHOOK_URL",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "openai_api_key": "OPENAI_API_KEY",
        "google_api_key": "GOOGLE_API_KEY",
    }
    updated = []
    for field, env_key in field_map.items():
        val = getattr(req, field)
        if val is not None:
            set_key(str(env_file), env_key, str(val))
            # Update in-memory settings (best-effort)
            try:
                current = getattr(settings, field)
                coerced = int(val) if isinstance(current, int) else str(val)
                object.__setattr__(settings, field, coerced)
            except Exception:
                pass
            updated.append(field)

    # Handle work_address geocoding
    if req.work_address is not None:
        import asyncio
        set_key(str(env_file), "WORK_ADDRESS", req.work_address)
        object.__setattr__(settings, "work_address", req.work_address)
        updated.append("work_address")
        coords = asyncio.run(_geocode_address(req.work_address)) if req.work_address.strip() else None
        if coords:
            work_lat, work_lng = coords
            set_key(str(env_file), "WORK_LAT", str(work_lat))
            set_key(str(env_file), "WORK_LNG", str(work_lng))
            object.__setattr__(settings, "work_lat", work_lat)
            object.__setattr__(settings, "work_lng", work_lng)
        else:
            set_key(str(env_file), "WORK_LAT", "")
            set_key(str(env_file), "WORK_LNG", "")
            object.__setattr__(settings, "work_lat", None)
            object.__setattr__(settings, "work_lng", None)

    smtp_fields = {"smtp_host", "smtp_port", "smtp_user", "smtp_password", "report_email", "report_hour", "report_minute"}
    restart_needed = bool(smtp_fields.intersection(updated))
    return {"status": "updated", "updated_fields": updated, "restart_required": restart_needed, "env_file": str(env_file)}


class SchedulerSettingsRequest(BaseModel):
    enabled: bool
    interval_minutes: int
    timezone: str = ""


@app.get("/api/settings/scheduler")
def get_scheduler_settings():
    """Return background polling configuration."""
    return {
        "enabled": settings.background_polling_enabled,
        "interval_minutes": settings.background_poll_interval_minutes,
        "timezone": settings.user_timezone,
    }


@app.post("/api/settings/scheduler")
def update_scheduler_settings(req: SchedulerSettingsRequest):
    """Update background polling interval/enabled state and reschedule jobs live."""
    try:
        from dotenv import set_key
    except ImportError:
        raise HTTPException(500, "python-dotenv not available")
    from homesearch.services.scheduler_service import reschedule_jobs

    env_file = _env_file_path()
    set_key(str(env_file), "BACKGROUND_POLLING_ENABLED", str(req.enabled).lower())
    set_key(str(env_file), "BACKGROUND_POLL_INTERVAL_MINUTES", str(req.interval_minutes))
    set_key(str(env_file), "USER_TIMEZONE", req.timezone)

    object.__setattr__(settings, "background_polling_enabled", req.enabled)
    object.__setattr__(settings, "background_poll_interval_minutes", req.interval_minutes)
    object.__setattr__(settings, "user_timezone", req.timezone)

    reschedule_jobs(req.interval_minutes, req.enabled)
    return {"status": "ok"}


@app.post("/api/settings/webhook/test")
def test_webhook():
    """Fire the global Zapier webhook with a real listing from the database."""
    import httpx
    webhook_url = settings.zapier_webhook_url
    if not webhook_url:
        return {"success": False, "message": "No webhook URL configured."}
    db.init_db()
    conn = db.get_connection()
    try:
        conn.row_factory = __import__("sqlite3").Row
        row = conn.execute(
            "SELECT * FROM listings WHERE price IS NOT NULL AND address IS NOT NULL ORDER BY last_seen_at DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {"success": False, "message": "No listings in database yet — run a search first."}
    r = dict(row)
    price_str = f"${int(r.get('price') or 0):,}" if r.get('price') else "Price N/A"
    stats_parts = []
    if r.get('bedrooms'): stats_parts.append(f"🛏 {r['bedrooms']} bd")
    if r.get('bathrooms'): stats_parts.append(f"🛁 {r['bathrooms']:.0f} ba")
    if r.get('sqft'): stats_parts.append(f"📐 {int(r['sqft']):,} sqft")
    detail_parts = []
    if r.get('year_built'): detail_parts.append(f"🏗 Built {r['year_built']}")
    if r.get('has_garage'): detail_parts.append("🚗 Garage")
    if r.get('has_basement'): detail_parts.append("🏚 Basement")
    city = r.get('city', '') or ''
    state = r.get('state', '') or ''
    location = ", ".join(p for p in [city, state] if p) or "Your Area"
    from homesearch.services.scheduler_service import _shorten_url
    url = r.get('source_url') or ''
    if not url and r.get('address'):
        query = "+".join(p for p in [r.get('address',''), city, state] if p)
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    url = _shorten_url(url)
    msg_lines = [
        "HomerFindr 🏠",
        f"New Listing in {location}",
    ]
    if url: msg_lines.append(f"🔗 {url}")
    msg_lines += [
        "",
        f"📍 {r.get('address', '')}",
        f"💰 {price_str}",
    ]
    if stats_parts: msg_lines.append(" · ".join(stats_parts))
    if detail_parts: msg_lines.append(" · ".join(detail_parts))
    formatted_message = "\n".join(msg_lines)

    payload = {
        "alert_type": "test",
        "search_name": "HomerFindr Test",
        "message": formatted_message,
        "address": r.get("address", ""),
        "city": r.get("city", ""),
        "state": r.get("state", ""),
        "zip_code": r.get("zip_code", ""),
        "price": r.get("price"),
        "bedrooms": r.get("bedrooms"),
        "bathrooms": r.get("bathrooms"),
        "sqft": r.get("sqft"),
        "year_built": r.get("year_built"),
        "days_on_mls": r.get("days_on_mls"),
        "url": r.get("source_url", ""),
        "photo_url": r.get("photo_url", ""),
    }
    try:
        resp = httpx.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        return {"success": True, "message": f"Webhook fired with listing: {r.get('address')}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/settings/smtp/test")
def test_smtp_connection():
    """Attempt an SMTP login to verify credentials."""
    import smtplib
    if not settings.smtp_user or not settings.smtp_password:
        return {"success": False, "message": "SMTP credentials not configured."}
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.ehlo()
            s.starttls()
            s.login(settings.smtp_user, settings.smtp_password)
        return {"success": True, "message": f"Connected to {settings.smtp_host}:{settings.smtp_port} — credentials valid."}
    except Exception as e:
        return {"success": False, "message": str(e)}


# --- Location autocomplete ---

@app.get("/api/locations/search")
def search_locations(q: str = ""):
    """Typeahead location search — returns unique city+state pairs."""
    from uszipcode import SearchEngine
    from homesearch.services.zip_service import _parse_city, _parse_state

    q = q.strip()
    if len(q) < 2:
        return {"suggestions": []}

    search = SearchEngine()

    city_part = _parse_city(q)
    state_part = _parse_state(q)

    # Try direct city search first; if no results, use fuzzy find_city candidates
    results = search.by_city(city=city_part, returns=50)
    if not results:
        try:
            candidates = search.find_city(city_part, best_match=False) or []
        except ValueError:
            candidates = []
        for candidate in candidates[:5]:
            r = search.by_city(city=candidate, returns=50)
            if r:
                results = r
                break

    # Filter to specified state if user typed one
    if state_part:
        results = [r for r in results if (r.state or "").upper() == state_part.upper()]

    # Build unique city+state suggestions
    seen = set()
    suggestions = []
    for r in results:
        city = r.major_city or r.post_office_city or ""
        state = r.state or ""
        key = f"{city.upper()}|{state.upper()}"
        if key not in seen and city:
            seen.add(key)
            suggestions.append({"city": city, "state": state})
        if len(suggestions) >= 8:
            break

    return {"suggestions": suggestions}


# --- Listing actions ---

@app.post("/api/listings/{listing_id}/starred")
def toggle_starred(listing_id: int, request: Request):
    """Toggle the saved/starred state of a listing for the current session."""
    session_id = _get_session(request)
    new_state = db.toggle_listing_starred(listing_id, session_id)
    return {"is_starred": new_state}


@app.get("/api/listings/all")
def get_all_listings():
    """Return all listings across every saved search, deduplicated."""
    db.init_db()
    results = db.get_all_listings()
    listing_ids = [r.id for r in results if r.id]
    price_changes = db.get_price_changes_for_listings(listing_ids)
    listings_out = []
    for r in results:
        d = r.model_dump()
        d["price_change"] = price_changes.get(r.id)
        listings_out.append(d)
    return {"results": listings_out, "total": len(listings_out)}


@app.get("/api/listings/starred")
def get_starred_listings(request: Request):
    """Get all saved/starred listings for the current session."""
    session_id = _get_session(request)
    listings = db.get_starred_listings(session_id)
    listing_ids = [l.id for l in listings if l.id]
    price_changes = db.get_price_changes_for_listings(listing_ids) if listing_ids else {}
    listings_out = []
    for l in listings:
        d = l.model_dump()
        d["price_change"] = price_changes.get(l.id)
        listings_out.append(d)
    return {"listings": listings_out, "total": len(listings_out)}


# --- Notification settings ---

class NotificationSettingsRequest(BaseModel):
    desktop: bool = True
    zapier_webhook: str = ""
    notify_coming_soon_only: bool = False
    alerts_paused: bool = False
    recipients: list[str] = []


@app.put("/api/searches/{search_id}/notifications")
def update_notification_settings(search_id: int, req: NotificationSettingsRequest):
    """Update notification settings for a saved search."""
    existing = db.get_saved_search(search_id)
    if not existing:
        raise HTTPException(404, "Search not found")
    ns = NotificationSettings(
        desktop=req.desktop,
        zapier_webhook=req.zapier_webhook,
        notify_coming_soon_only=req.notify_coming_soon_only,
        alerts_paused=req.alerts_paused,
        recipients=req.recipients,
    )
    db.update_search(search_id, notification_settings=ns)
    return {"status": "updated", "notification_settings": ns.model_dump()}


# --- Session management ---

def _get_session(request: Request) -> str:
    """Extract session ID from X-HF-Session header, falling back to 'default'."""
    return request.headers.get("X-HF-Session", "default") or "default"


@app.post("/api/session/init")
def session_init(request: Request):
    """Register a device session and migrate legacy 'default' data on first use.
    If HOUSEHOLD_SESSION is set in .env, ALL devices share that session (opt-in sync).
    Otherwise each device keeps its own session — no forced sharing."""
    client_session = request.headers.get("X-HF-Session", "").strip().upper()

    if settings.household_session:
        # Explicit household sharing — all devices adopt the shared session
        session_id = settings.household_session
        # Migrate dismissed listings from the device's old session if it's switching
        if client_session and client_session != session_id and len(client_session) == 6 and client_session.isalnum():
            try:
                conn = db.get_connection()
                conn.execute(
                    "INSERT OR IGNORE INTO dismissed_listings (source_id, session_id, dismissed_at) "
                    "SELECT source_id, ?, dismissed_at FROM dismissed_listings WHERE session_id = ?",
                    (session_id, client_session),
                )
                conn.commit()
                conn.close()
            except Exception:
                pass
    elif client_session and len(client_session) == 6 and client_session.isalnum():
        # Per-device isolation — respect the client's own session
        session_id = client_session
    else:
        # No usable session (shouldn't happen since frontend auto-generates)
        return {"session_id": None}

    # Register session and migrate legacy 'default' data on first use
    is_new = db.create_session(session_id)
    if is_new:
        db.migrate_default_to_session(session_id)

    return {"session_id": session_id}


@app.post("/api/searches/{search_id}/mark-seen")
def mark_search_seen(search_id: int):
    """Mark all listings in a search as seen (clears the 'new' flag)."""
    db.mark_results_not_new(search_id)
    return {"status": "ok"}


# --- Network info ---

@app.get("/api/network-info")
def network_info(request: Request):
    """Return the LAN-accessible URL for QR code sharing."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = request.headers.get("host", "localhost").split(":")[0]
    port = settings.port
    return {"url": f"http://{lan_ip}:{port}"}


# --- Push notification endpoints ---

class PushSubscribeRequest(BaseModel):
    id: str
    endpoint: str
    p256dh: str
    auth: str

@app.post("/api/push/subscribe")
def push_subscribe(req: PushSubscribeRequest):
    db.save_push_subscription(req.id, req.endpoint, req.p256dh, req.auth)
    return {"status": "subscribed"}

@app.delete("/api/push/subscribe/{sub_id}")
def push_unsubscribe(sub_id: str):
    db.delete_push_subscription(sub_id)
    return {"status": "unsubscribed"}

@app.get("/api/push/vapid-public-key")
def get_vapid_public_key():
    return {"key": settings.vapid_public_key}


# --- Dismissed listings endpoints ---

@app.post("/api/listings/{source_id}/dismiss")
def dismiss_listing(source_id: str, request: Request):
    session_id = _get_session(request)
    db.dismiss_listing(source_id, session_id=session_id)
    return {"status": "dismissed"}

@app.delete("/api/listings/{source_id}/dismiss")
def undismiss_listing(source_id: str, request: Request):
    session_id = _get_session(request)
    db.undismiss_listing(source_id, session_id=session_id)
    return {"status": "undismissed"}

@app.get("/api/listings/dismissed")
def get_dismissed(request: Request):
    session_id = _get_session(request)
    return {"dismissed": list(db.get_dismissed_source_ids(session_id=session_id))}


# --- Offer estimation ---

@app.post("/api/offer-estimate")
def get_offer_estimate(listing: Listing):
    """Run logical CMA + optional AI offer estimate for a listing."""
    from homesearch.services.offer_service import get_offer_estimate as _estimate
    result = _estimate(listing)
    return result.model_dump()


@app.get("/api/listings/{listing_id}/comps")
def get_listing_comps(listing_id: int):
    """Fetch recently sold comparable listings for a saved listing."""
    import traceback
    listing = db.get_listing_by_id(listing_id)
    if not listing:
        # Try fetching from all listings (in case the listing isn't in DB but was passed by id)
        raise HTTPException(404, f"Listing {listing_id} not found in database")
    try:
        from homesearch.services.offer_service import get_comparable_listings
        comps = get_comparable_listings(listing)
        return {"comps": [c.model_dump() for c in comps], "total": len(comps)}
    except Exception as e:
        traceback.print_exc()
        # Return empty rather than a 500 — comps are best-effort
        return {"comps": [], "total": 0, "error": str(e)}


# --- Polygon → zip codes endpoint ---

@app.post("/api/zips/from-polygon")
def zips_from_polygon(body: dict):
    """Given a GeoJSON polygon (list of [lng, lat] pairs), return zip codes whose centroids fall within it."""
    from uszipcode import SearchEngine
    coords = body.get("coordinates", [])  # list of [lng, lat]
    if len(coords) < 3:
        return {"zip_codes": []}

    def point_in_polygon(px, py, polygon):
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    # Get bounding box of polygon for efficient pre-filter
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)

    # Use bounding box center + diagonal radius to fetch candidates, then filter with point-in-polygon
    import math
    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2
    # Rough radius in miles: half-diagonal of bounding box (1 deg lat ≈ 69 mi, 1 deg lng ≈ 53 mi at 40°N)
    lat_miles = (max_lat - min_lat) * 69 / 2
    lng_miles = (max_lng - min_lng) * 53 / 2
    radius_miles = math.ceil(math.sqrt(lat_miles ** 2 + lng_miles ** 2)) + 5  # +5 buffer

    engine = SearchEngine()
    results = engine.by_coordinates(center_lat, center_lng, radius=radius_miles, returns=500)

    # Filter to centroids actually inside the polygon
    # polygon is [lng, lat] but point_in_polygon expects (x=lng, y=lat)
    matching = [
        r.zipcode for r in results
        if r.lat and r.lng and point_in_polygon(r.lng, r.lat, coords)
    ]
    return {"zip_codes": matching[:50]}  # cap at 50 zips


# --- CLI launcher ---

@app.post("/api/system/open-cli")
def open_cli():
    """Open a terminal window running the homesearch CLI (local machine only)."""
    import platform
    import shutil
    import subprocess
    system = platform.system()
    # Prefer the full path so new shell sessions don't need to resolve PATH
    exe = shutil.which("homesearch") or "homesearch"
    try:
        if system == "Darwin":
            # Source shell profiles so PATH is correct, then run homesearch
            shell_cmd = (
                f'source ~/.zprofile 2>/dev/null; source ~/.zshrc 2>/dev/null; '
                f'source ~/.bash_profile 2>/dev/null; source ~/.bashrc 2>/dev/null; '
                f'{exe}'
            )
            subprocess.Popen([
                "osascript",
                "-e", "tell application \"Terminal\"",
                "-e", "activate",
                "-e", f"do script \"{shell_cmd}\"",
                "-e", "end tell",
            ])
        elif system == "Windows":
            subprocess.Popen(
                ["cmd.exe", "/k", exe],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            for term in ["gnome-terminal", "xterm", "konsole", "xfce4-terminal"]:
                try:
                    subprocess.Popen([term, "-e", exe])
                    break
                except FileNotFoundError:
                    continue
        return {"success": True, "platform": system, "exe": exe}
    except Exception as e:
        return {"success": False, "error": str(e), "platform": system}


# --- Serve frontend static files ---

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Never cache index.html so browsers always load the latest build
        return FileResponse(
            str(FRONTEND_DIR / "index.html"),
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
