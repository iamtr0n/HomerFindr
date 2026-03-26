const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  // Searches
  listSearches: () => request('/searches'),
  getSearch: (id) => request(`/searches/${id}`),
  createSearch: (criteria, name) => request('/searches', {
    method: 'POST',
    body: JSON.stringify({ criteria, save_as: name }),
  }),
  runSearch: (id) => request(`/searches/${id}/run`, { method: 'POST' }),
  deleteSearch: (id) => request(`/searches/${id}`, { method: 'DELETE' }),
  getResults: (id, newOnly = false) => request(`/searches/${id}/results?new_only=${newOnly}`),
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

  // Reports
  generateReport: () => request('/report/generate', { method: 'POST' }),
  sendReport: () => request('/report/send', { method: 'POST' }),
}

export async function streamSearch(criteria, { onProgress, onResults, onError } = {}) {
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
