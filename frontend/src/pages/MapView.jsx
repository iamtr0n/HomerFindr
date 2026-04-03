import { useState, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Map, X, Loader2, Search, LocateFixed } from 'lucide-react'
import { api } from '../api'
import ListingMap from '../components/ListingMap'

export default function MapView() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [banner, setBanner] = useState(null)
  const [flyTarget, setFlyTarget] = useState(null)
  const [userLocation, setUserLocation] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [locLoading, setLocLoading] = useState(false)
  const [locError, setLocError] = useState('')
  const inputRef = useRef(null)

  const allListingsQuery = useQuery({ queryKey: ['all-listings'], queryFn: api.getAllListings })
  const dismissedQuery = useQuery({ queryKey: ['dismissed'], queryFn: api.getDismissed })
  const dismissedIds = useMemo(() => new Set(dismissedQuery.data?.dismissed || []), [dismissedQuery.data])

  const dismissMutation = useMutation({
    mutationFn: (sourceId) => api.dismissListing(sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dismissed'] }),
  })

  const listings = useMemo(() => {
    const raw = allListingsQuery.data?.results || []
    const seen = new Set()
    return raw.filter(l => {
      if (!l.latitude || !l.longitude) return false
      if (dismissedIds.has(l.source_id)) return false
      if (seen.has(l.source_id)) return false
      seen.add(l.source_id)
      return true
    })
  }, [allListingsQuery.data, dismissedIds])

  const polygonMutation = useMutation({
    mutationFn: (coords) => api.zipFromPolygon(coords),
    onSuccess: (result) => setBanner({ zipCodes: result.zips?.map(z => z.zipcode) ?? [] }),
  })

  const handlePolygon = (coords) => {
    setBanner(null)
    polygonMutation.mutate(coords)
  }

  const handleNewSearch = () => {
    if (!banner?.zipCodes?.length) return
    navigate(`/search/new?zips=${banner.zipCodes.join(',')}`)
  }

  const handleSearch = async (e) => {
    e?.preventDefault()
    const q = searchQuery.trim()
    if (!q) return
    setSearchLoading(true)
    setLocError('')
    try {
      const isZip = /^\d{5}$/.test(q)
      const searchUrl = isZip
        ? `https://nominatim.openstreetmap.org/search?postalcode=${q}&country=us&format=json&limit=1`
        : `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&countrycodes=us&format=json&limit=1`
      const res = await fetch(searchUrl, { headers: { 'Accept-Language': 'en' } })
      const data = await res.json()
      if (data.length > 0) {
        setFlyTarget({ lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon), zoom: 13 })
      } else {
        setLocError('Location not found')
      }
    } catch {
      setLocError('Search failed')
    } finally {
      setSearchLoading(false)
    }
  }

  const handleMyLocation = () => {
    if (!navigator.geolocation) { setLocError('Geolocation not supported'); return }
    setLocLoading(true)
    setLocError('')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude }
        setUserLocation(loc)
        setFlyTarget({ ...loc, zoom: 14 })
        setLocLoading(false)
      },
      () => { setLocError('Location access denied'); setLocLoading(false) }
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Map size={20} className="text-amber-400" />
          <h1 className="font-serif text-2xl text-ink-primary">Map View</h1>
        </div>
        <span className="text-xs text-ink-muted">Draw a polygon to define your search area</span>
      </div>

      {/* Search + location controls */}
      <div className="flex items-center gap-2">
        <form onSubmit={handleSearch} className="flex flex-1 items-center gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted pointer-events-none" />
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search a location…"
              className="w-full pl-8 pr-3 py-2 bg-canvas-800 border border-canvas-600 rounded-lg text-sm text-ink-secondary placeholder:text-ink-muted focus:border-amber-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={searchLoading || !searchQuery.trim()}
            className="px-3 py-2 text-sm bg-canvas-800 border border-canvas-600 rounded-lg text-ink-secondary hover:border-amber-500 hover:text-amber-400 transition-colors disabled:opacity-40"
          >
            {searchLoading ? <Loader2 size={14} className="animate-spin" /> : 'Go'}
          </button>
        </form>
        <button
          onClick={handleMyLocation}
          disabled={locLoading}
          title="Jump to my location"
          className="flex items-center gap-1.5 px-3 py-2 text-sm bg-canvas-800 border border-canvas-600 rounded-lg text-ink-secondary hover:border-amber-500 hover:text-amber-400 transition-colors disabled:opacity-40 shrink-0"
        >
          {locLoading ? <Loader2 size={14} className="animate-spin" /> : <LocateFixed size={14} />}
          <span className="hidden sm:inline">My Location</span>
        </button>
      </div>

      {locError && <p className="text-xs text-red-400">{locError}</p>}

      {/* Polygon result banner */}
      {polygonMutation.isPending && (
        <div className="flex items-center gap-2 px-4 py-3 bg-canvas-800 border border-canvas-600 rounded-xl text-ink-secondary text-sm">
          <Loader2 size={14} className="animate-spin text-amber-400" />
          Finding zip codes in your drawn area…
        </div>
      )}

      {banner && (
        <div className="flex flex-wrap items-center gap-3 px-4 py-3 bg-amber-500/10 border border-amber-500/40 rounded-xl">
          <p className="text-sm text-ink-primary flex-1">
            {banner.zipCodes.length > 0 ? (
              <>Found <span className="font-mono font-semibold text-amber-400">{banner.zipCodes.length}</span> zip code{banner.zipCodes.length !== 1 ? 's' : ''} in area — use these in a new search</>
            ) : (
              'No zip codes found in the drawn area. Try a larger polygon.'
            )}
          </p>
          <div className="flex items-center gap-2 shrink-0">
            {banner.zipCodes.length > 0 && (
              <button onClick={handleNewSearch} className="px-3 py-1.5 text-xs font-medium bg-amber-500 hover:bg-amber-400 text-canvas-950 rounded-lg transition-colors">
                New Search with This Area
              </button>
            )}
            <button onClick={() => setBanner(null)} className="p-1 text-ink-muted hover:text-ink-primary transition-colors">
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Instructions */}
      <p className="text-xs text-ink-muted">
        Draw a polygon or rectangle on the map to find zip codes in an area, then start a new search.
      </p>

      {/* Map */}
      <div className="rounded-xl border border-canvas-700" style={{ height: '70vh', overflow: 'hidden' }}>
        <ListingMap
          listings={listings}
          onPolygonComplete={handlePolygon}
          flyTarget={flyTarget}
          userLocation={userLocation}
          onDismiss={(sourceId) => dismissMutation.mutate(sourceId)}
        />
      </div>
    </div>
  )
}
