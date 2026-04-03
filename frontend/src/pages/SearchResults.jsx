import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import PropertyCard from '../components/PropertyCard'
import { Button } from '../components/ui/Button'
import { ArrowLeft, Play, Loader2, Filter } from 'lucide-react'
import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import { useMortgage } from '../components/MortgageBar'
import { estimateCommute } from '../utils/commute'

function readViewedIds() {
  try { return new Set(JSON.parse(localStorage.getItem('homerfindr_viewed') || '[]')) } catch { return new Set() }
}

export default function SearchResults() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { settings: mortgageSettings } = useMortgage()
  const { data: settingsData } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings, staleTime: 300000 })
  const workLocation = (settingsData?.work_lat && settingsData?.work_lng)
    ? { lat: settingsData.work_lat, lng: settingsData.work_lng }
    : null
  const [showNewOnly, setShowNewOnly] = useState(false)
  const [sortBy, setSortBy] = useState('match_score')
  const [hideViewed, setHideViewed] = useState(false)
  const [viewedIds] = useState(() => readViewedIds())
  const [filterMinPrice, setFilterMinPrice] = useState('')
  const [filterMaxPrice, setFilterMaxPrice] = useState('')
  const [filterMinBeds, setFilterMinBeds] = useState('')
  const [filterMinBaths, setFilterMinBaths] = useState('')
  const [providerErrors, setProviderErrors] = useState([])
  const [showStrictBanner, setShowStrictBanner] = useState(false)

  const queryClient = useQueryClient()

  const searchQuery = useQuery({ queryKey: ['search', id], queryFn: () => api.getSearch(id) })
  const resultsQuery = useQuery({
    queryKey: ['results', id, showNewOnly],
    queryFn: () => api.getResults(id, showNewOnly),
    refetchInterval: 60 * 1000,
  })
  const dismissedQuery = useQuery({ queryKey: ['dismissed'], queryFn: api.getDismissed })
  const dismissedIds = useMemo(() => new Set(dismissedQuery.data?.dismissed || []), [dismissedQuery.data])

  const runMutation = useMutation({
    mutationFn: () => api.runSearch(id),
    onSuccess: (data) => {
      setProviderErrors(data.provider_errors || [])
      setShowNewOnly(true)
      resultsQuery.refetch()
      searchQuery.refetch()
      if (queryClient.getQueryData(['search', id])?.criteria?.style_strict) setShowStrictBanner(true)
    },
  })

  const updateMutation = useMutation({
    mutationFn: (criteria) => api.updateSearch(id, criteria, search?.name),
    onSuccess: () => { searchQuery.refetch(); runMutation.mutate() },
  })

  const starMutation = useMutation({ mutationFn: (listingId) => api.toggleStarred(listingId) })
  const dismissMutation = useMutation({
    mutationFn: (sourceId) => api.dismissListing(sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dismissed'] }),
  })
  const handleDismiss = useCallback((sourceId) => { dismissMutation.mutate(sourceId) }, [dismissMutation])

  // Mark listings as seen once when results first load — clears the "New" badge server-side
  const markedSeenRef = useRef(false)
  useEffect(() => {
    if (!markedSeenRef.current && resultsQuery.data && !showNewOnly) {
      markedSeenRef.current = true
      api.markSeen(id).then(() => {
        queryClient.invalidateQueries({ queryKey: ['searches'] })
      }).catch(() => {})
    }
  }, [resultsQuery.data, id, showNewOnly, queryClient])

  const search = searchQuery.data
  const allResults = resultsQuery.data?.results || []
  const results = useMemo(() => allResults.filter(l => !dismissedIds.has(l.source_id)), [allResults, dismissedIds])
  const maxScore = results.length > 0 ? Math.max(...results.map(r => r.match_score || 0), 1) : 1

  const displayed = useMemo(() => {
    let list = [...results]
    if (filterMinPrice) list = list.filter(l => (l.price || 0) >= +filterMinPrice)
    if (filterMaxPrice) list = list.filter(l => !l.price || l.price <= +filterMaxPrice)
    if (filterMinBeds) list = list.filter(l => (l.bedrooms || 0) >= +filterMinBeds)
    if (filterMinBaths) list = list.filter(l => (l.bathrooms || 0) >= +filterMinBaths)
    if (hideViewed) list = list.filter(l => !viewedIds.has(l.source_id))
    switch (sortBy) {
      case 'match_score': list.sort((a, b) => {
        const d = (b.match_score || 0) - (a.match_score || 0)
        if (d !== 0) return d
        return (b.is_gold_star ? 1 : 0) - (a.is_gold_star ? 1 : 0)
      }); break
      case 'price_asc':  list.sort((a, b) => (a.price || 0) - (b.price || 0)); break
      case 'price_desc': list.sort((a, b) => (b.price || 0) - (a.price || 0)); break
      case 'sqft_desc':  list.sort((a, b) => (b.sqft || 0) - (a.sqft || 0)); break
      case 'newest':     list.sort((a, b) => (b.year_built || 0) - (a.year_built || 0)); break
    }
    if (!hideViewed && viewedIds.size > 0) {
      const unviewed = list.filter(l => !viewedIds.has(l.source_id))
      const viewed = list.filter(l => viewedIds.has(l.source_id))
      list = [...unviewed, ...viewed]
    }
    return list
  }, [results, filterMinPrice, filterMaxPrice, filterMinBeds, filterMinBaths, hideViewed, viewedIds, sortBy])
  const forSaleListings = displayed.filter(l => l.listing_type !== 'pending' && l.listing_type !== 'coming_soon')
  const pendingListings = displayed.filter(l => l.listing_type === 'pending' || l.listing_type === 'coming_soon')

  const filterPill = (active, onClick, children) => (
    <button
      onClick={onClick}
      className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
        active
          ? 'bg-amber-500/10 border-amber-500/50 text-amber-400'
          : 'border-canvas-600 text-ink-secondary hover:border-canvas-500'
      }`}
    >
      {children}
    </button>
  )

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/')} className="text-ink-muted hover:text-ink-primary transition-colors">
          <ArrowLeft size={22} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="font-serif text-2xl text-ink-primary truncate">
            {search?.name || 'Search Results'}
          </h1>
          {search?.criteria?.location && (
            <p className="text-sm text-ink-muted">
              {search.criteria.location}
              {search.criteria.radius_miles && ` · ${search.criteria.radius_miles}mi radius`}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="font-mono text-sm text-ink-muted">
            {forSaleListings.length} for sale{pendingListings.length > 0 ? ` · ${pendingListings.length} pending` : ''}
          </span>
          <Button onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
            {runMutation.isPending ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
            Refresh
          </Button>
        </div>
      </div>

      {/* Provider errors */}
      {providerErrors.length > 0 && (
        <div className="bg-match-warn/10 border border-match-warn/30 rounded-xl p-4 mb-4">
          <p className="text-sm text-match-warn font-medium mb-1">Some providers had issues:</p>
          <ul className="text-sm text-match-warn/80 list-disc list-inside">
            {providerErrors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}

      {/* Strict style filter banner */}
      {showStrictBanner && (
        <div className="flex items-center justify-between bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-3 mb-4 gap-3">
          <p className="text-sm text-amber-300">
            <span className="font-semibold">Strict style filter is ON.</span> Some listings may be hidden because their style couldn't be confirmed. Want to turn it off to see more?
          </p>
          <div className="flex gap-2 shrink-0">
            <button
              onClick={() => setShowStrictBanner(false)}
              className="text-xs text-ink-muted hover:text-ink-secondary px-2 py-1"
            >
              Keep strict
            </button>
            <button
              onClick={() => {
                updateMutation.mutate({ ...search.criteria, style_strict: false })
                setShowStrictBanner(false)
              }}
              className="text-xs px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-canvas-950 font-semibold rounded-lg transition-colors"
            >
              Turn off & re-run
            </button>
          </div>
        </div>
      )}

      {/* Filters bar */}
      <div className="sticky top-16 z-10 bg-canvas-900/90 backdrop-blur border-b border-canvas-700 -mx-6 px-6 py-3 mb-6 flex flex-wrap items-center gap-2">
        <Filter size={14} className="text-ink-muted shrink-0" />

        {filterPill(showNewOnly, () => setShowNewOnly(!showNewOnly), 'New only')}

        {viewedIds.size > 0 && filterPill(
          hideViewed,
          () => setHideViewed(!hideViewed),
          hideViewed ? `Show viewed (${viewedIds.size})` : `Hide viewed (${viewedIds.size})`
        )}

        {/* Price inputs */}
        <div className="flex items-center gap-1">
          <input
            type="number"
            placeholder="Min $"
            value={filterMinPrice}
            onChange={(e) => setFilterMinPrice(e.target.value)}
            className="w-24 py-1 px-2 bg-canvas-800 border border-canvas-600 rounded-lg text-xs text-ink-secondary placeholder:text-ink-muted focus:border-amber-500 focus:outline-none"
          />
          <span className="text-ink-muted text-xs">–</span>
          <input
            type="number"
            placeholder="Max $"
            value={filterMaxPrice}
            onChange={(e) => setFilterMaxPrice(e.target.value)}
            className="w-24 py-1 px-2 bg-canvas-800 border border-canvas-600 rounded-lg text-xs text-ink-secondary placeholder:text-ink-muted focus:border-amber-500 focus:outline-none"
          />
        </div>

        {/* Beds */}
        <select
          value={filterMinBeds}
          onChange={(e) => setFilterMinBeds(e.target.value)}
          className="py-1 px-2 bg-canvas-800 border border-canvas-600 rounded-lg text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
        >
          <option value="">Beds</option>
          {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}+ bd</option>)}
        </select>

        {/* Baths */}
        <select
          value={filterMinBaths}
          onChange={(e) => setFilterMinBaths(e.target.value)}
          className="py-1 px-2 bg-canvas-800 border border-canvas-600 rounded-lg text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
        >
          <option value="">Baths</option>
          {[1,2,3].map(n => <option key={n} value={n}>{n}+ ba</option>)}
        </select>

        {/* Sort */}
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="ml-auto py-1 px-2 bg-canvas-800 border border-canvas-600 rounded-lg text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
        >
          <option value="match_score">⭐ Best Match</option>
          <option value="price_asc">Price ↑</option>
          <option value="price_desc">Price ↓</option>
          <option value="sqft_desc">Largest</option>
          <option value="newest">Newest</option>
        </select>
      </div>

      {/* Results */}
      {resultsQuery.isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={32} className="animate-spin text-amber-500" />
        </div>
      ) : results.length === 0 ? (
        <div className="text-center py-16 bg-canvas-900 rounded-xl border border-canvas-700">
          <p className="text-ink-secondary text-lg mb-4">
            {showNewOnly ? 'No new listings since last check' : 'No cached results'}
          </p>
          <Button onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
            Run Search Now
          </Button>
        </div>
      ) : (
        <>
          {/* For Sale */}
          {forSaleListings.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {forSaleListings.map((listing, i) => (
                <PropertyCard
                  key={`${listing.source}-${listing.source_id}-${i}`}
                  listing={listing}
                  isViewed={viewedIds.has(listing.source_id)}
                  maxScore={maxScore}
                  onToggleStar={starMutation.mutate}
                  mortgageSettings={mortgageSettings.enabled ? mortgageSettings : null}
                  onDismiss={handleDismiss}
                  commuteMinutes={workLocation && listing.latitude && listing.longitude
                    ? estimateCommute(listing.latitude, listing.longitude, workLocation.lat, workLocation.lng)
                    : null}
                />
              ))}
            </div>
          )}

          {/* Pending */}
          {pendingListings.length > 0 && (
            <div className="mt-10">
              <div className="flex items-center gap-3 mb-4">
                <h2 className="font-serif text-xl text-ink-primary">Pending</h2>
                <span className="font-mono text-xs text-ink-muted bg-canvas-800 border border-canvas-600 px-2 py-0.5 rounded-full">
                  {pendingListings.length}
                </span>
                <span className="text-xs text-ink-muted">These were active listings now under contract</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 opacity-75">
                {pendingListings.map((listing, i) => (
                  <PropertyCard
                    key={`${listing.source}-${listing.source_id}-${i}`}
                    listing={listing}
                    isViewed={viewedIds.has(listing.source_id)}
                    maxScore={maxScore}
                    onToggleStar={starMutation.mutate}
                    mortgageSettings={mortgageSettings.enabled ? mortgageSettings : null}
                    onDismiss={handleDismiss}
                    commuteMinutes={workLocation && listing.latitude && listing.longitude
                      ? estimateCommute(listing.latitude, listing.longitude, workLocation.lat, workLocation.lng)
                      : null}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
