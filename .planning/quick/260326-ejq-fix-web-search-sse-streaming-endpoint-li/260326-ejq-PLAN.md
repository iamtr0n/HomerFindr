---
phase: quick
plan: 260326-ejq
type: execute
wave: 1
depends_on: []
files_modified:
  - homesearch/api/routes.py
  - frontend/src/api.js
  - frontend/src/pages/NewSearch.jsx
  - frontend/src/components/SearchForm.jsx
autonomous: true
requirements: [SSE-streaming, progress-bar, remove-zip-gate]

must_haves:
  truths:
    - "User types a location, clicks Search, and sees a live progress bar showing ZIP N/M being searched"
    - "Search completes and property cards render without the user ever clicking Find ZIPs"
    - "The browser never appears stuck — progress updates stream in real time"
  artifacts:
    - path: "homesearch/api/routes.py"
      provides: "POST /api/search/stream SSE endpoint"
      contains: "StreamingResponse"
    - path: "frontend/src/api.js"
      provides: "streamSearch function with ReadableStream parsing"
      exports: ["streamSearch"]
    - path: "frontend/src/pages/NewSearch.jsx"
      provides: "Live progress bar replacing static spinner"
      contains: "progress"
    - path: "frontend/src/components/SearchForm.jsx"
      provides: "Simplified search flow — no Find ZIPs gate"
  key_links:
    - from: "frontend/src/pages/NewSearch.jsx"
      to: "frontend/src/api.js"
      via: "streamSearch(criteria, onProgress, onResults)"
      pattern: "streamSearch"
    - from: "frontend/src/api.js"
      to: "/api/search/stream"
      via: "fetch with ReadableStream reader"
      pattern: "fetch.*search/stream"
    - from: "homesearch/api/routes.py"
      to: "homesearch/services/search_service.py"
      via: "run_search(criteria, on_progress=callback) in background thread"
      pattern: "run_search.*on_progress"
---

<objective>
Fix web search so it actually returns homes with live progress feedback instead of appearing stuck.

Purpose: The web search takes ~75s (50 ZIPs x 1.5s rate limit) with zero feedback, making the browser appear frozen. Additionally, users must manually click "Find ZIPs" before searching, which is unnecessary since `run_search` auto-discovers ZIPs when `zip_codes=[]`.

Output: SSE streaming endpoint, frontend stream consumer with progress bar, simplified search flow.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

<interfaces>
<!-- Key contracts the executor needs -->

From homesearch/providers/base.py:
```python
# on_progress callback signature used by all providers
on_progress: optional callable(current: int, total: int, location: str)
```

From homesearch/services/search_service.py:
```python
def run_search(
    criteria: SearchCriteria,
    search_id: Optional[int] = None,
    use_zip_discovery: bool = True,
    errors: Optional[list] = None,
    pre_filter_counts: Optional[list] = None,
    on_progress=None,
) -> list[Listing]:
```

From homesearch/api/routes.py:
```python
class SearchRequest(BaseModel):
    criteria: SearchCriteria
    save_as: Optional[str] = None

class SearchResponse(BaseModel):
    results: list[Listing]
    total: int
    search_id: Optional[int] = None
    search_name: Optional[str] = None
    provider_errors: list[str] = []
```

From frontend/src/api.js:
```javascript
const BASE = '/api'
// Existing pattern: api.previewSearch(criteria) calls POST /api/search/preview
```

From frontend/src/components/SearchForm.jsx:
```javascript
// Current props: { onResults, onLoading }
// handleSearch calls api.previewSearch(buildCriteria()) or api.createSearch(...)
// discoverZips must be clicked manually before searching
```

From frontend/src/pages/NewSearch.jsx:
```javascript
// Current: <SearchForm onResults={handleResults} onLoading={setLoading} />
// Shows <Loader2> spinner during loading — no progress info
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add SSE streaming endpoint to backend</name>
  <files>homesearch/api/routes.py</files>
  <action>
Add a `POST /api/search/stream` endpoint to `homesearch/api/routes.py` that streams search progress via Server-Sent Events.

Implementation:
1. Add imports at top: `import asyncio`, `import threading`, `import json`, `from fastapi.responses import StreamingResponse`

2. Create the endpoint function:
```python
@app.post("/api/search/stream")
async def stream_search(req: SearchRequest):
    """Run a search with SSE progress streaming."""
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def on_progress(current: int, total: int, location: str):
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
```

3. Place this endpoint AFTER the existing `preview_search` route and BEFORE the `create_and_run_search` route (line ~60 area). It must be above the catch-all `/{full_path:path}` frontend route.

Key details:
- `run_search` is synchronous and blocking (provider rate limits), so it MUST run in a thread
- `asyncio.Queue` + `loop.call_soon_threadsafe` bridges the thread back to the async event loop
- The `on_progress(current, total, location)` signature matches what all providers already call
- `model_dump()` serializes Listing Pydantic models to dicts for JSON
- The generator breaks after emitting the "results" event so the connection closes
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "from homesearch.api.routes import app; routes = [r.path for r in app.routes]; assert '/api/search/stream' in routes, f'Missing /api/search/stream in {routes}'; print('SSE endpoint registered')"</automated>
  </verify>
  <done>POST /api/search/stream endpoint exists, accepts SearchRequest, returns StreamingResponse with text/event-stream media type</done>
</task>

<task type="auto">
  <name>Task 2: Add streamSearch to frontend API + wire progress bar and simplified search flow</name>
  <files>frontend/src/api.js, frontend/src/pages/NewSearch.jsx, frontend/src/components/SearchForm.jsx</files>
  <action>
**A) frontend/src/api.js** — Add `streamSearch` function after the existing `api` export:

```javascript
export async function streamSearch(criteria, { onProgress, onResults, onError }) {
  const res = await fetch(`${BASE}/search/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ criteria }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() // keep incomplete line in buffer

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const msg = JSON.parse(line.slice(6))
        if (msg.type === 'progress') onProgress?.(msg)
        else if (msg.type === 'results') onResults?.(msg)
      } catch (e) {
        // skip malformed lines
      }
    }
  }
}
```

**B) frontend/src/components/SearchForm.jsx** — Simplify the search flow:

1. Change the component signature from `{ onResults, onLoading }` to `{ onSearch, onLoading }`. The parent (NewSearch) will handle the streaming, not SearchForm.

2. Replace the `handleSearch` function body. Instead of calling `api.previewSearch` or `api.createSearch`, just call:
```javascript
const handleSearch = async (save = false) => {
  const c = buildCriteria()
  onSearch?.(c, save ? saveName : null)
}
```
SearchForm no longer does the API call itself — it builds criteria and delegates to the parent.

3. Keep the "Find ZIPs" button but make it purely optional/informational. Change its label from "Find ZIPs" to "Preview ZIPs". It still calls `discoverZips()` and shows the ZIP chips, but the Search button works regardless of whether ZIPs were discovered. Remove the condition that gates searching on ZIP discovery — the Search button should only require `criteria.location` to be non-empty (which it already does via `disabled={loading || !criteria.location}`).

4. Add `{ value: 'coming_soon', label: 'Coming Soon' }` to the `LISTING_TYPES` array at the top.

**C) frontend/src/pages/NewSearch.jsx** — Wire streaming + progress bar:

1. Add new state:
```javascript
const [progress, setProgress] = useState(null) // { current, total, location }
```

2. Add import for `streamSearch`:
```javascript
import { streamSearch } from '../api'
```

3. Replace `handleResults` with a new `handleSearch` that uses streaming:
```javascript
const handleSearch = async (criteria, saveName) => {
  setLoading(true)
  setResults(null)
  setProgress(null)
  setProviderErrors([])

  try {
    await streamSearch(criteria, {
      onProgress: (msg) => setProgress(msg),
      onResults: (msg) => {
        setResults(msg)
        setProviderErrors(msg.provider_errors || [])
        setProgress(null)
        setLoading(false)
      },
      onError: (err) => {
        console.error('Stream error:', err)
        setLoading(false)
        setProgress(null)
      },
    })
  } catch (e) {
    console.error('Search failed:', e)
    setLoading(false)
    setProgress(null)
  }
}
```

4. Update SearchForm usage — change props from `onResults={handleResults} onLoading={setLoading}` to `onSearch={handleSearch} onLoading={setLoading}`:
```jsx
<SearchForm onSearch={handleSearch} onLoading={setLoading} />
```

5. Replace the loading spinner block (the `{loading && (...)}` section with the `Loader2` spinner) with a progress bar:
```jsx
{loading && (
  <div className="py-8">
    {progress ? (
      <div className="max-w-lg mx-auto">
        <div className="flex justify-between text-sm text-slate-600 mb-2">
          <span>Searching ZIP {progress.current}/{progress.total}</span>
          <span>{Math.round((progress.current / progress.total) * 100)}%</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${(progress.current / progress.total) * 100}%` }}
          />
        </div>
        <p className="text-xs text-slate-500 mt-2 text-center">{progress.location}</p>
      </div>
    ) : (
      <div className="flex items-center justify-center gap-3 text-brand-600">
        <Loader2 size={24} className="animate-spin" />
        <span className="text-lg">Starting search...</span>
      </div>
    )}
  </div>
)}
```

Remove the `Loader2` import only if it's no longer used elsewhere in the file. It IS still used in the fallback "Starting search..." state, so keep the import.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr/frontend && npx --yes acorn --ecma2020 --module src/api.js > /dev/null 2>&1 && echo "api.js parses OK" && npx --yes acorn-jsx --ecma2020 src/pages/NewSearch.jsx > /dev/null 2>&1 || node -e "try { require('fs').readFileSync('src/pages/NewSearch.jsx','utf8'); console.log('NewSearch.jsx exists') } catch(e) { process.exit(1) }" && node -e "const s = require('fs').readFileSync('src/api.js','utf8'); if(!s.includes('streamSearch')) { console.error('Missing streamSearch'); process.exit(1) } console.log('streamSearch found in api.js')" && node -e "const s = require('fs').readFileSync('src/pages/NewSearch.jsx','utf8'); if(!s.includes('progress')) { console.error('Missing progress'); process.exit(1) } console.log('progress bar found in NewSearch.jsx')" && node -e "const s = require('fs').readFileSync('src/components/SearchForm.jsx','utf8'); if(!s.includes('coming_soon')) { console.error('Missing coming_soon'); process.exit(1) } console.log('Coming Soon found in SearchForm.jsx')"</automated>
  </verify>
  <done>
    - `streamSearch` exported from api.js and uses ReadableStream to parse SSE events
    - NewSearch.jsx shows live progress bar with "Searching ZIP N/M" and percentage during search
    - SearchForm.jsx calls `onSearch(criteria, saveName)` callback instead of calling API directly
    - "Find ZIPs" button relabeled to "Preview ZIPs" and is optional (not required before searching)
    - "Coming Soon" added to LISTING_TYPES
    - `npm run build` succeeds in frontend/
  </done>
</task>

</tasks>

<verification>
1. Start the backend: `cd /Users/iamtron/Documents/GitHub/HomerFindr && python -m homesearch serve`
2. In another terminal, build and verify frontend: `cd frontend && npm run build`
3. Visit http://127.0.0.1:8000, go to New Search
4. Type a location (e.g., "Atlanta, GA"), click Search directly (without clicking Preview ZIPs)
5. Observe: progress bar shows "Searching ZIP 1/N ... 2/N ..." with a filling blue bar
6. After ~75s, results appear as property cards
7. Verify "Coming Soon" appears in the listing type buttons
</verification>

<success_criteria>
- Web search returns homes without requiring manual ZIP discovery
- Live progress bar shows current/total ZIP progress during search
- Browser never appears stuck — SSE events stream in real time
- "Coming Soon" listing type is visible in the search form
- Frontend builds without errors
</success_criteria>

<output>
After completion, create `.planning/quick/260326-ejq-fix-web-search-sse-streaming-endpoint-li/260326-ejq-SUMMARY.md`
</output>
