"""FastAPI REST API for the web frontend."""

import asyncio
import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from homesearch import database as db
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


@app.post("/api/search/preview", response_model=SearchResponse)
def preview_search(req: SearchRequest):
    """Run a search without saving it."""
    provider_errors: list[str] = []
    results = run_search(req.criteria, errors=provider_errors)
    return SearchResponse(results=results, total=len(results),
                          provider_errors=provider_errors)


@app.post("/api/search/stream")
async def stream_search(req: SearchRequest):
    """Run a search with SSE progress streaming."""
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def on_progress(current: int, total: int, location: str, found: int = 0):
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {"type": "progress", "current": current, "total": total, "location": location}
        )

    def run_in_thread():
        provider_errors: list[str] = []
        results = run_search(req.criteria, errors=provider_errors, on_progress=on_progress)
        loop.call_soon_threadsafe(
            queue.put_nowait,
            {
                "type": "results",
                "results": [r.model_dump() for r in results],
                "total": len(results),
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
def create_and_run_search(req: SearchRequest):
    """Create a saved search and run it immediately."""
    name = req.save_as or f"Search {req.criteria.location}"
    saved = SavedSearch(name=name, criteria=req.criteria)
    search_id = db.save_search(saved)
    provider_errors: list[str] = []
    results = run_search(req.criteria, search_id=search_id, errors=provider_errors)
    return SearchResponse(
        results=results, total=len(results),
        search_id=search_id, search_name=name,
        provider_errors=provider_errors,
    )


@app.get("/api/searches")
def list_searches():
    """List all saved searches."""
    searches = db.get_saved_searches()
    return {"searches": [s.model_dump() for s in searches]}


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
def get_search_results(search_id: int, new_only: bool = False):
    """Get cached results for a saved search."""
    search = db.get_saved_search(search_id)
    if not search:
        raise HTTPException(404, "Search not found")
    results = db.get_search_results(search_id, new_only=new_only)
    return {"results": [r.model_dump() for r in results], "total": len(results)}


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


# --- Notification settings ---

class NotificationSettingsRequest(BaseModel):
    desktop: bool = True
    zapier_webhook: str = ""
    notify_coming_soon_only: bool = False


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
    )
    db.update_search(search_id, notification_settings=ns)
    return {"status": "updated", "notification_settings": ns.model_dump()}


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
        return FileResponse(str(FRONTEND_DIR / "index.html"))
