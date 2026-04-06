const BASE = '/api'

// --- Session management ---
// Session ID is a 6-char alphanumeric code scoped to this device/household member.
// It is extracted from ?s=CODE on first load (QR code share), then persisted to localStorage.

function _loadSession() {
  // Check URL for ?s=CODE first (QR code scan / explicit share)
  const params = new URLSearchParams(window.location.search)
  const fromUrl = params.get('s')
  if (fromUrl && /^[A-Z0-9]{6}$/i.test(fromUrl)) {
    localStorage.setItem('hf_session', fromUrl.toUpperCase())
    const clean = window.location.pathname + window.location.hash
    window.history.replaceState({}, '', clean)
    return fromUrl.toUpperCase()
  }
  // Auto-generate a session on first visit so queries never fall through to 'default'
  let stored = localStorage.getItem('hf_session')
  if (!stored) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    stored = Array.from({ length: 6 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
    localStorage.setItem('hf_session', stored)
  }
  return stored
}

let _sessionId = _loadSession()

export function getSessionId() {
  return _sessionId
}

export function setSessionId(id) {
  _sessionId = id
  localStorage.setItem('hf_session', id)
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (_sessionId) headers['X-HF-Session'] = _sessionId
  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  // Session
  initSession: () => request('/session/init', { method: 'POST' }),

  // Searches
  listSearches: () => request('/searches'),
  getSearch: (id) => request(`/searches/${id}`),
  createSearch: (criteria, name) => request('/searches', {
    method: 'POST',
    body: JSON.stringify({ criteria, save_as: name }),
  }),
  runSearch: (id) => request(`/searches/${id}/run`, { method: 'POST' }),
  updateSearch: (id, criteria, name) => request(`/searches/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ criteria, save_as: name }),
  }),
  deleteSearch: (id) => request(`/searches/${id}`, { method: 'DELETE' }),
  setSearchActive: (id, is_active) => request(`/searches/${id}/active`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active }),
  }),
  openCli: () => request('/system/open-cli', { method: 'POST' }),
  getResults: (id, newOnly = false) => request(`/searches/${id}/results?new_only=${newOnly}`),
  markSeen: (id) => request(`/searches/${id}/mark-seen`, { method: 'POST' }),
  // FIX-01: verified — paths match, no double /api prefix
  // BASE='/api' + '/search/preview' → fetch('/api/search/preview')
  // Vite proxy: /api/* → http://127.0.0.1:8000/api/* → backend @app.post("/api/search/preview")
  previewSearch: (criteria) => request('/search/preview', {
    method: 'POST',
    body: JSON.stringify({ criteria }),
  }),

  // Location autocomplete
  searchLocations: (query) =>
    request(`/locations/search?q=${encodeURIComponent(query)}`),

  // ZIP discovery
  discoverZips: (location, radius = 25) =>
    request(`/zips/discover?location=${encodeURIComponent(location)}&radius=${radius}`),

  // Notification settings
  updateNotifications: (id, settings) => request(`/searches/${id}/notifications`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  }),

  // Listing actions
  toggleStarred: (id) => request(`/listings/${id}/starred`, { method: 'POST' }),
  getStarredListings: () => request('/listings/starred'),
  getAllListings: () => request('/listings/all'),
  zipFromPolygon: (coords) => request('/zips/from-polygon', { method: 'POST', body: JSON.stringify({ coordinates: coords }) }),

  // Reports
  generateReport: () => request('/report/generate', { method: 'POST' }),
  sendReport: () => request('/report/send', { method: 'POST' }),

  // Version
  getVersion: () => request('/version'),

  // Settings
  getSettingsStatus: () => request('/settings/status'),
  getSettings: () => request('/settings'),
  updateSettings: (data) => request('/settings', { method: 'PUT', body: JSON.stringify(data) }),
  testSmtp: () => request('/settings/smtp/test', { method: 'POST' }),
  testWebhook: () => request('/settings/webhook/test', { method: 'POST' }),

  // Scheduler / background polling
  getSchedulerSettings: () => request('/settings/scheduler'),
  updateSchedulerSettings: (data) => request('/settings/scheduler', { method: 'POST', body: JSON.stringify(data) }),

  // Network info (LAN IP for QR code)
  getNetworkInfo: () => request('/network-info'),

  // Web Push subscriptions
  getVapidPublicKey: () => request('/push/vapid-public-key'),
  subscribePush: (sub) => request('/push/subscribe', { method: 'POST', body: JSON.stringify(sub) }),
  unsubscribePush: (id) => request(`/push/subscribe/${id}`, { method: 'DELETE' }),

  // Offer estimation
  getOfferEstimate: (listing) => request('/offer-estimate', {
    method: 'POST',
    body: JSON.stringify(listing),
  }),

  // Comparable sales
  getComps: (id) => request(`/listings/${id}/comps`),

  // Dismissed listings (server-side sync)
  getDismissed: () => request('/listings/dismissed'),
  dismissListing: (sourceId) => request(`/listings/${encodeURIComponent(sourceId)}/dismiss`, { method: 'POST' }),
  undismissListing: (sourceId) => request(`/listings/${encodeURIComponent(sourceId)}/dismiss`, { method: 'DELETE' }),
}

export async function streamSearch(criteria, saveName, { onProgress, onPartial, onResults, onError } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (_sessionId) headers['X-HF-Session'] = _sessionId
  const res = await fetch(`${BASE}/search/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ criteria, save_as: saveName || null }),
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
        else if (msg.type === 'partial') onPartial?.(msg)
        else if (msg.type === 'results') onResults?.(msg)
      } catch (e) {
        // skip malformed lines
      }
    }
  }
}
