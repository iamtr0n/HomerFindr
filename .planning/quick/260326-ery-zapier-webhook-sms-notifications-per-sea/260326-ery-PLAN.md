---
phase: quick
plan: 260326-ery
type: execute
wave: 1
depends_on: []
files_modified:
  - homesearch/models.py
  - homesearch/database.py
  - homesearch/services/scheduler_service.py
  - homesearch/api/routes.py
  - frontend/src/api.js
  - frontend/src/pages/Dashboard.jsx
autonomous: true
must_haves:
  truths:
    - "Each saved search has independent notification settings (desktop toggle, webhook URL, coming-soon-only toggle)"
    - "When alert_job finds new listings, it POSTs a JSON payload to the Zapier webhook URL if configured"
    - "Coming-soon-only filter suppresses non-coming-soon alerts when enabled"
    - "Searches with a webhook URL poll at 3-minute intervals instead of 10"
    - "User can configure notification settings per search via the Dashboard UI"
  artifacts:
    - path: "homesearch/models.py"
      provides: "NotificationSettings model nested in SavedSearch"
      contains: "class NotificationSettings"
    - path: "homesearch/database.py"
      provides: "notification_settings_json column migration and read/write support"
      contains: "notification_settings_json"
    - path: "homesearch/services/scheduler_service.py"
      provides: "Webhook POST logic and per-search poll interval"
      contains: "zapier_webhook"
    - path: "homesearch/api/routes.py"
      provides: "PUT /api/searches/{id}/notifications endpoint"
      contains: "notifications"
    - path: "frontend/src/api.js"
      provides: "updateNotifications API method"
      contains: "updateNotifications"
    - path: "frontend/src/pages/Dashboard.jsx"
      provides: "Alerts settings panel per saved search card"
      contains: "NotificationSettings"
  key_links:
    - from: "frontend/src/pages/Dashboard.jsx"
      to: "/api/searches/{id}/notifications"
      via: "api.updateNotifications fetch call"
      pattern: "updateNotifications"
    - from: "homesearch/services/scheduler_service.py"
      to: "SavedSearch.notification_settings.zapier_webhook"
      via: "httpx.post to webhook URL with listing payload"
      pattern: "httpx\\.post.*zapier_webhook"
    - from: "homesearch/database.py"
      to: "homesearch/models.py:NotificationSettings"
      via: "JSON serialization/deserialization of notification_settings_json column"
      pattern: "notification_settings"
---

<objective>
Add per-search notification settings with Zapier webhook support so the user gets SMS/email alerts (via Zapier) when new listings are found, even when away from their computer.

Purpose: Desktop-only notifications are useless when the user is away. Zapier webhooks enable SMS, email, Slack -- any channel the user configures in their Zap.
Output: NotificationSettings model, DB migration, webhook dispatch in scheduler, API endpoint, and Dashboard UI panel.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@homesearch/models.py
@homesearch/database.py
@homesearch/services/scheduler_service.py
@homesearch/api/routes.py
@frontend/src/api.js
@frontend/src/pages/Dashboard.jsx

<interfaces>
<!-- Existing patterns the executor must follow -->

From homesearch/models.py:
```python
class SavedSearch(BaseModel):
    id: Optional[int] = None
    name: str
    criteria: SearchCriteria
    created_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    is_active: bool = True
    result_count: int = 0
```

From homesearch/database.py:
```python
# SavedSearch is stored in saved_searches table with criteria_json TEXT column
# New columns added via ALTER TABLE in init_db() with try/except for idempotency
# get_saved_searches() manually constructs SavedSearch from row dict
# update_search(search_id, **kwargs) handles dynamic column updates
```

From homesearch/services/scheduler_service.py:
```python
def alert_job():
    # Iterates active_searches, calls run_search, finds new_listings
    # Currently only sends macOS osascript desktop notification
    # Runs on IntervalTrigger(minutes=10)
```

From homesearch/api/routes.py:
```python
# Pattern: db.get_saved_search(id) -> raise HTTPException(404) if not found
# Pattern: db.update_search(search_id, **kwargs) for updates
# Uses Pydantic BaseModel for request bodies
```

From frontend/src/api.js:
```javascript
export const api = {
  // Pattern: methodName: (args) => request('/path', { method, body })
  listSearches: () => request('/searches'),
  deleteSearch: (id) => request(`/searches/${id}`, { method: 'DELETE' }),
}
```

From frontend/src/pages/Dashboard.jsx:
```jsx
// Pattern: useMutation + queryClient.invalidateQueries for mutations
// Pattern: Card > CardHeader + CardContent layout per saved search
// Pattern: Button with variant="default"|"outline"|"ghost" and size="sm"|"icon"
// Icons from lucide-react
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend -- Model, DB migration, API endpoint, and scheduler webhook dispatch</name>
  <files>homesearch/models.py, homesearch/database.py, homesearch/api/routes.py, homesearch/services/scheduler_service.py</files>
  <action>
**homesearch/models.py** -- Add `NotificationSettings` Pydantic model and attach to `SavedSearch`:

```python
class NotificationSettings(BaseModel):
    """Per-search notification preferences."""
    desktop: bool = True                    # macOS osascript notification
    zapier_webhook: str = ""                # Zapier webhook URL (empty = disabled)
    notify_coming_soon_only: bool = False   # Only alert on coming_soon listing_type
```

Add to `SavedSearch`:
```python
notification_settings: NotificationSettings = Field(default_factory=NotificationSettings)
```

Place `NotificationSettings` class ABOVE `SavedSearch` so the forward reference resolves.

**homesearch/database.py** -- Add column migration and read/write support:

1. In `init_db()`, add an ALTER TABLE migration block (same idempotent try/except pattern as existing filter columns):
```python
try:
    conn.execute("ALTER TABLE saved_searches ADD COLUMN notification_settings_json TEXT DEFAULT '{}'")
    conn.commit()
except Exception:
    pass  # Column already exists
```

2. In `get_saved_searches()` and `get_saved_search()` and `get_saved_search_by_name()` -- when constructing `SavedSearch`, add:
```python
notification_settings=NotificationSettings.model_validate_json(
    row["notification_settings_json"] or "{}"
)
```
Import `NotificationSettings` from models at the top of the file.

3. In `update_search()`, add a handler in the kwargs loop for `notification_settings`:
```python
elif k == "notification_settings":
    sets.append("notification_settings_json = ?")
    vals.append(v.model_dump_json() if hasattr(v, "model_dump_json") else json.dumps(v))
```

**homesearch/api/routes.py** -- Add PUT endpoint for notification settings:

Add a request model:
```python
from homesearch.models import NotificationSettings

class NotificationSettingsRequest(BaseModel):
    desktop: bool = True
    zapier_webhook: str = ""
    notify_coming_soon_only: bool = False
```

Add endpoint (place it BEFORE the catch-all `serve_frontend` route):
```python
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
```

**homesearch/services/scheduler_service.py** -- Update `alert_job` for webhook + coming_soon filter + dynamic intervals:

1. Add `import httpx` at the top of `alert_job` (lazy import, httpx is already a dependency).

2. After `new_listings` is computed, read notification settings:
```python
ns = s.notification_settings
```

3. Apply coming_soon filter: If `ns.notify_coming_soon_only` is True, filter `new_listings` to only those where `l.listing_type == "coming_soon"`. If the filtered list is empty, skip alerting for this search.

4. Wrap existing osascript block in `if ns.desktop:` guard.

5. After desktop notification, add webhook dispatch:
```python
if ns.zapier_webhook:
    try:
        payload = {
            "search_name": s.name,
            "new_count": len(new_listings),
            "listing_type": s.criteria.listing_type.value if hasattr(s.criteria.listing_type, 'value') else str(s.criteria.listing_type),
            "listings": [
                {
                    "address": l.address,
                    "city": l.city,
                    "state": l.state,
                    "zip_code": l.zip_code,
                    "price": l.price,
                    "beds": l.bedrooms,
                    "baths": l.bathrooms,
                    "sqft": l.sqft,
                    "url": l.source_url,
                    "listing_type": l.listing_type,
                }
                for l in new_listings[:10]  # Cap at 10 to avoid huge payloads
            ],
        }
        httpx.post(ns.zapier_webhook, json=payload, timeout=10)
        print(f"[Alerts] Webhook sent for '{s.name}' ({len(new_listings)} listings)")
    except Exception as e:
        print(f"[Alerts] Webhook error for '{s.name}': {e}")
```

6. For dynamic poll intervals: Replace the single `alert_job` with TWO scheduled jobs in `start_scheduler()`:
   - `realtime_alerts` at 10-min interval (existing, for all active searches WITHOUT webhook)
   - `webhook_alerts` at 3-min interval (new, for active searches WITH webhook set)

   Refactor: Extract alert logic into a helper `_check_search(s)` that both jobs call. The 10-min job filters to searches where `notification_settings.zapier_webhook == ""`, and the 3-min job filters to searches where `notification_settings.zapier_webhook != ""`.

   ```python
   _scheduler.add_job(
       webhook_alert_job,
       trigger=IntervalTrigger(minutes=3),
       id="webhook_alerts",
       name="Webhook Listing Alerts (3min)",
       replace_existing=True,
   )
   ```
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr && python -c "
from homesearch.models import SavedSearch, NotificationSettings
ns = NotificationSettings(desktop=True, zapier_webhook='https://hooks.zapier.com/test', notify_coming_soon_only=True)
ss = SavedSearch(name='test', criteria={}, notification_settings=ns)
assert ss.notification_settings.zapier_webhook == 'https://hooks.zapier.com/test'
assert ss.notification_settings.notify_coming_soon_only == True
j = ns.model_dump_json()
ns2 = NotificationSettings.model_validate_json(j)
assert ns2.zapier_webhook == ns.zapier_webhook
print('Models OK')

from homesearch.database import init_db
init_db()
print('DB migration OK')

from homesearch.api.routes import app
routes = [r.path for r in app.routes]
assert '/api/searches/{search_id}/notifications' in routes, f'Missing route. Found: {routes}'
print('API route OK')
print('ALL CHECKS PASSED')
"</automated>
  </verify>
  <done>NotificationSettings model exists on SavedSearch, DB column migrated, PUT /api/searches/{id}/notifications endpoint responds, scheduler dispatches webhooks for searches with webhook URLs and respects coming_soon filter and desktop toggle.</done>
</task>

<task type="auto">
  <name>Task 2: Frontend -- API method and Dashboard alerts UI panel</name>
  <files>frontend/src/api.js, frontend/src/pages/Dashboard.jsx</files>
  <action>
**frontend/src/api.js** -- Add notification settings methods:

```javascript
// In the api object, add:
updateNotifications: (id, settings) => request(`/searches/${id}/notifications`, {
  method: 'PUT',
  body: JSON.stringify(settings),
}),
```

**frontend/src/pages/Dashboard.jsx** -- Add alerts settings panel per search card:

1. Add imports: `import { useState } from 'react'` (add to existing useMemo import line), `Bell` and `Save` from `lucide-react`.

2. Add state for tracking which search card has its alerts panel open:
```javascript
const [alertsOpen, setAlertsOpen] = useState(null) // search ID or null
```

3. Add state for form values:
```javascript
const [alertForm, setAlertForm] = useState({ desktop: true, zapier_webhook: '', notify_coming_soon_only: false })
```

4. Add mutation:
```javascript
const notifMutation = useMutation({
  mutationFn: ({ id, settings }) => api.updateNotifications(id, settings),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['searches'] })
    setAlertsOpen(null)
  },
})
```

5. In each search card's button row (the `<div className="flex gap-2">` block), add a Bell button BEFORE the delete button:
```jsx
<Button
  variant="ghost"
  size="icon"
  onClick={() => {
    if (alertsOpen === s.id) {
      setAlertsOpen(null)
    } else {
      setAlertForm({
        desktop: s.notification_settings?.desktop ?? true,
        zapier_webhook: s.notification_settings?.zapier_webhook ?? '',
        notify_coming_soon_only: s.notification_settings?.notify_coming_soon_only ?? false,
      })
      setAlertsOpen(s.id)
    }
  }}
>
  <Bell size={16} className={s.notification_settings?.zapier_webhook ? 'text-brand-600' : 'text-slate-400'} />
</Button>
```

6. BELOW the button row div but still inside `<CardContent>`, add the collapsible alerts panel (only shown when `alertsOpen === s.id`):

```jsx
{alertsOpen === s.id && (
  <div className="mt-3 pt-3 border-t border-slate-100 space-y-3">
    <p className="text-sm font-medium text-slate-700">Alert Settings</p>

    {/* Desktop toggle */}
    <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
      <input
        type="checkbox"
        checked={alertForm.desktop}
        onChange={(e) => setAlertForm(f => ({ ...f, desktop: e.target.checked }))}
        className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
      />
      Desktop notifications
    </label>

    {/* Zapier webhook URL */}
    <div>
      <label className="block text-sm text-slate-600 mb-1">Zapier Webhook URL</label>
      <input
        type="url"
        value={alertForm.zapier_webhook}
        onChange={(e) => setAlertForm(f => ({ ...f, zapier_webhook: e.target.value }))}
        placeholder="https://hooks.zapier.com/hooks/catch/..."
        className="w-full px-2.5 py-1.5 text-sm border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
      />
    </div>

    {/* Coming Soon only toggle */}
    <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
      <input
        type="checkbox"
        checked={alertForm.notify_coming_soon_only}
        onChange={(e) => setAlertForm(f => ({ ...f, notify_coming_soon_only: e.target.checked }))}
        className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
      />
      Coming Soon listings only
    </label>

    {/* Save button */}
    <Button
      variant="default"
      size="sm"
      className="w-full"
      onClick={() => notifMutation.mutate({ id: s.id, settings: alertForm })}
      disabled={notifMutation.isPending}
    >
      {notifMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
      Save Alert Settings
    </Button>
  </div>
)}
```

Important: The `notification_settings` field comes from the API response (`api.listSearches` returns search objects). Since we added `notification_settings` to `SavedSearch` with a default, the `model_dump()` call in `list_searches` endpoint will automatically include it. No API response changes needed.
  </action>
  <verify>
    <automated>cd /Users/iamtron/Documents/GitHub/HomerFindr/frontend && npx vite build 2>&1 | tail -5</automated>
  </verify>
  <done>Dashboard shows a Bell icon per search card that opens an inline alert settings panel with desktop toggle, webhook URL input, and coming-soon-only toggle. Saving calls PUT /api/searches/{id}/notifications and refreshes the search list. Bell icon is highlighted (brand color) when a webhook is configured.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Per-search notification settings with Zapier webhook integration. Each saved search card on the Dashboard now has a Bell icon that opens an alert settings panel with: desktop notification toggle, Zapier webhook URL field, and "Coming Soon only" toggle. The scheduler sends HTTP POST payloads to configured webhook URLs when new listings are found.</what-built>
  <how-to-verify>
    1. Start the app: `cd /Users/iamtron/Documents/GitHub/HomerFindr && homesearch serve`
    2. Open http://127.0.0.1:8000 in your browser
    3. Go to the Dashboard -- you should see your saved searches
    4. Click the Bell icon on any saved search card
    5. Verify the alert settings panel opens with three controls: desktop toggle, webhook URL input, coming-soon-only toggle
    6. Paste a test Zapier webhook URL (or use https://webhook.site for testing) and click Save
    7. Verify the Bell icon turns brand-colored (indicating webhook is configured)
    8. Click Bell again to confirm settings persisted (re-opens with saved values)
    9. Optional: Run the search and wait 3 minutes to verify webhook fires, or manually trigger via:
       `curl -X POST "your-webhook-url" -H "Content-Type: application/json" -d '{"search_name":"test","new_count":1,"listings":[{"address":"123 Main St","price":450000}]}'`
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<verification>
- `python -c "from homesearch.models import NotificationSettings; print('OK')"` -- model importable
- `python -c "from homesearch.database import init_db; init_db(); print('OK')"` -- DB migration runs
- `curl -s http://127.0.0.1:8000/api/searches | python -m json.tool` -- notification_settings appears in response
- `cd frontend && npx vite build` -- frontend compiles without errors
</verification>

<success_criteria>
- NotificationSettings model with desktop, zapier_webhook, notify_coming_soon_only fields
- DB column notification_settings_json migrated on init
- PUT /api/searches/{id}/notifications endpoint saves settings
- Scheduler sends webhook POST with listing payload when new matches found
- Searches with webhook configured poll every 3 minutes (others stay at 10)
- Coming-soon-only filter suppresses non-coming-soon alerts
- Dashboard Bell icon opens inline settings panel per search card
- Frontend builds successfully
</success_criteria>

<output>
After completion, create `.planning/quick/260326-ery-zapier-webhook-sms-notifications-per-sea/260326-ery-SUMMARY.md`
</output>
