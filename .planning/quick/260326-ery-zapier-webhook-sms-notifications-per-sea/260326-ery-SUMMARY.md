---
phase: quick
plan: 260326-ery
subsystem: notifications
tags: [zapier, webhook, alerts, scheduler, dashboard]
dependency_graph:
  requires: []
  provides: [per-search-notification-settings, zapier-webhook-dispatch, alerts-panel-ui]
  affects: [homesearch/models.py, homesearch/database.py, homesearch/services/scheduler_service.py, homesearch/api/routes.py, frontend/src/api.js, frontend/src/pages/Dashboard.jsx]
tech_stack:
  added: []
  patterns: [pydantic-json-column, apscheduler-dual-jobs, tanstack-mutation-inline-panel]
key_files:
  created: []
  modified:
    - homesearch/models.py
    - homesearch/database.py
    - homesearch/services/scheduler_service.py
    - homesearch/api/routes.py
    - frontend/src/api.js
    - frontend/src/pages/Dashboard.jsx
decisions:
  - "Used httpx (already a dep) instead of urllib for webhook POST — cleaner API, already imported by other deps"
  - "Refactored alert_job into _check_search helper shared by two interval jobs (10min desktop, 3min webhook)"
  - "Placed NotificationSettings class above SavedSearch in models.py so forward reference resolves without TYPE_CHECKING"
metrics:
  duration: "~3 minutes"
  completed: "2026-03-26T14:50:54Z"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 6
---

# Quick Task 260326-ery: Zapier Webhook SMS Notifications per Search — Summary

**One-liner:** Per-search Zapier webhook alerts with `NotificationSettings` model, idempotent DB column migration, `_check_search` helper dispatcher, dual-interval scheduler (3min/10min), PUT endpoint, and Dashboard Bell icon panel.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Backend — Model, DB migration, API endpoint, scheduler webhook dispatch | 91572bc | homesearch/models.py, homesearch/database.py, homesearch/api/routes.py, homesearch/services/scheduler_service.py |
| 2 | Frontend — API method and Dashboard alerts UI panel | 09b89f5 | frontend/src/api.js, frontend/src/pages/Dashboard.jsx |
| 3 | Human verification checkpoint | SKIPPED | — |

## What Was Built

### Backend (Task 1)

**`homesearch/models.py`**
- Added `NotificationSettings(BaseModel)` with `desktop: bool = True`, `zapier_webhook: str = ""`, `notify_coming_soon_only: bool = False`
- Added `notification_settings: NotificationSettings = Field(default_factory=NotificationSettings)` to `SavedSearch`

**`homesearch/database.py`**
- Added `NotificationSettings` import
- `init_db()`: idempotent `ALTER TABLE saved_searches ADD COLUMN notification_settings_json TEXT DEFAULT '{}'`
- All three `SavedSearch` construction sites (`get_saved_searches`, `get_saved_search`, `get_saved_search_by_name`) now deserialize `notification_settings_json` via `NotificationSettings.model_validate_json(row["notification_settings_json"] or "{}")`
- `update_search()`: added `notification_settings` kwarg handler that serializes via `model_dump_json()`

**`homesearch/api/routes.py`**
- Imported `NotificationSettings`
- Added `NotificationSettingsRequest(BaseModel)` request model
- Added `PUT /api/searches/{search_id}/notifications` endpoint — reads existing search, constructs `NotificationSettings`, calls `db.update_search(search_id, notification_settings=ns)`, returns `{status, notification_settings}`

**`homesearch/services/scheduler_service.py`**
- Extracted `_check_search(s)` inner helper: fetches new listings, applies coming_soon filter, sends desktop notification if `ns.desktop`, POSTs webhook payload if `ns.zapier_webhook` using `httpx.post`
- `alert_job()`: filters to searches without webhook → calls `_check_search` (10-min interval)
- `webhook_alert_job()`: filters to searches with webhook → calls `_check_search` (3-min interval)
- Both jobs registered in `start_scheduler()` with `replace_existing=True`

### Frontend (Task 2)

**`frontend/src/api.js`**
- Added `updateNotifications: (id, settings) => request('/searches/${id}/notifications', { method: 'PUT', body: JSON.stringify(settings) })`

**`frontend/src/pages/Dashboard.jsx`**
- Added `useState` to React import, `Bell` and `Save` to lucide-react imports
- Added `alertsOpen` (search ID | null) and `alertForm` state
- Added `notifMutation` using `useMutation` → calls `api.updateNotifications`, invalidates `['searches']`, closes panel on success
- Per card: Bell button opens/closes inline panel, pre-populates form from `s.notification_settings`
- Bell icon class: `text-brand-600` when webhook configured, `text-slate-400` otherwise
- Alert panel: desktop checkbox, Zapier webhook URL input, coming-soon-only checkbox, Save button

## Verification Results

All automated checks passed:
- `NotificationSettings` model importable and round-trips via JSON
- `SavedSearch` carries `notification_settings` field correctly
- `init_db()` runs without error (migration idempotent)
- `PUT /api/searches/{search_id}/notifications` route registered in FastAPI
- Frontend Vite build: 1613 modules, 0 errors, 929ms

## Deviations from Plan

None — plan executed exactly as written. The plan specified `httpx` (already a dependency), which was used as directed.

## Known Stubs

None. All data is wired end-to-end: `notification_settings` is serialized to/from DB, returned in `list_searches` API response (via `model_dump()`), and pre-populates the Dashboard form.

## Self-Check: PASSED

All 6 modified files exist. Both task commits (91572bc, 09b89f5) confirmed in git log.
