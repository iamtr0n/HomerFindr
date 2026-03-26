---
phase: quick
plan: 260326-ejq
subsystem: web-search
tags: [sse, streaming, progress-bar, search-flow, fastapi, react]
dependency_graph:
  requires: []
  provides: [POST /api/search/stream, streamSearch frontend function, live progress bar]
  affects: [frontend/src/api.js, frontend/src/pages/NewSearch.jsx, frontend/src/components/SearchForm.jsx, homesearch/api/routes.py]
tech_stack:
  added: [asyncio.Queue, threading.Thread, StreamingResponse, ReadableStream SSE parser]
  patterns: [thread-to-async-bridge via call_soon_threadsafe, SSE event stream, parent-controlled search flow]
key_files:
  created: []
  modified:
    - homesearch/api/routes.py
    - frontend/src/api.js
    - frontend/src/pages/NewSearch.jsx
    - frontend/src/components/SearchForm.jsx
decisions:
  - asyncio.Queue + loop.call_soon_threadsafe bridges blocking run_search thread back to async FastAPI event loop
  - SearchForm delegates criteria building to parent (NewSearch) rather than calling API itself — cleaner separation
  - Loader2 spinner kept for "Starting search..." fallback before first progress event arrives
metrics:
  duration: ~12 minutes
  completed: 2026-03-26
  tasks_completed: 2
  files_modified: 4
---

# Quick Task 260326-ejq: Fix Web Search SSE Streaming Endpoint Summary

**One-liner:** FastAPI SSE endpoint streams ZIP-by-ZIP progress via asyncio.Queue + thread bridge; React consumes ReadableStream with live progress bar replacing static spinner.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add POST /api/search/stream SSE endpoint | 979bd06 | homesearch/api/routes.py |
| 2 | streamSearch + progress bar + simplified SearchForm | c113300 | frontend/src/api.js, NewSearch.jsx, SearchForm.jsx |

## What Was Built

### Backend: `POST /api/search/stream`

Added to `homesearch/api/routes.py`. The endpoint:

1. Creates an `asyncio.Queue` and captures the current event loop
2. Starts `run_search` in a `daemon=True` background thread (required — `run_search` blocks on provider rate limits)
3. The `on_progress(current, total, location)` callback uses `loop.call_soon_threadsafe(queue.put_nowait, ...)` to safely deliver events from the thread back to the async event loop
4. `event_generator()` async generator pulls from the queue and yields SSE-formatted strings until the `"results"` event is received
5. Returns `StreamingResponse(event_generator(), media_type="text/event-stream")` with `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers

### Frontend: `streamSearch` in `api.js`

Named export `streamSearch(criteria, { onProgress, onResults, onError })` that:
- POSTs to `/api/search/stream`
- Uses `res.body.getReader()` + `TextDecoder` with `{ stream: true }` for chunked decoding
- Maintains a line buffer, splits on `\n`, and parses `data: {...}` SSE lines
- Dispatches `onProgress` for `type: "progress"` events, `onResults` for `type: "results"`

### Frontend: `NewSearch.jsx` — live progress bar

- Added `progress` state (`{ current, total, location }`)
- `handleSearch(criteria, saveName)` calls `streamSearch` with callbacks — no direct API call in SearchForm anymore
- Loading state shows progress bar (when `progress` exists) or "Starting search..." spinner (before first event):
  - Progress bar: "Searching ZIP N/M" label, percentage, animated blue fill bar, location label below
- `<SearchForm onSearch={handleSearch} onLoading={setLoading} />`

### Frontend: `SearchForm.jsx` — simplified flow

- Prop signature changed from `{ onResults, onLoading }` to `{ onSearch, onLoading }`
- `handleSearch` now only calls `onSearch?.(buildCriteria(), save ? saveName : null)` — no async work
- Removed local `loading` state (no longer needed; parent owns loading state)
- Search and Save & Search buttons no longer disabled on `loading`
- "Find ZIPs" renamed to "Preview ZIPs" — ZIP discovery is now purely optional/informational
- Added `{ value: 'coming_soon', label: 'Coming Soon' }` to `LISTING_TYPES`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All data paths are wired end-to-end.

## Self-Check: PASSED

- `homesearch/api/routes.py` contains `StreamingResponse` and `/api/search/stream`: confirmed
- `frontend/src/api.js` exports `streamSearch`: confirmed (grep count: 1)
- `frontend/src/pages/NewSearch.jsx` contains `progress`: confirmed (grep count: 6)
- `frontend/src/components/SearchForm.jsx` contains `coming_soon`: confirmed (grep count: 1)
- Frontend build: `✓ built in 981ms` — no errors
- Backend route check: `SSE endpoint registered` — confirmed
- Commits: 979bd06 (backend), c113300 (frontend) — both present
