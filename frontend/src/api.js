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
  previewSearch: (criteria) => request('/search/preview', {
    method: 'POST',
    body: JSON.stringify({ criteria }),
  }),

  // ZIP discovery
  discoverZips: (location, radius = 25) =>
    request(`/zips/discover?location=${encodeURIComponent(location)}&radius=${radius}`),

  // Reports
  generateReport: () => request('/report/generate', { method: 'POST' }),
  sendReport: () => request('/report/send', { method: 'POST' }),
}
