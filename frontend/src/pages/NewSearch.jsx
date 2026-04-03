import { useState, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import SearchForm from '../components/SearchForm'
import PropertyCard from '../components/PropertyCard'
import { useMortgage } from '../components/MortgageBar'
import ThumbnailCard from '../components/ThumbnailCard'
import PriceRangeSlider from '../components/PriceRangeSlider'
import SearchProgressTerminal from '../components/SearchProgressTerminal'
import { LayoutGrid, LayoutList, X } from 'lucide-react'
import { streamSearch } from '../api'

const SECTION_STYLES = {
  perfect: {
    border: 'border-match-perfect/40',
    header: 'bg-match-perfect/10 text-match-perfect border-b border-match-perfect/30',
  },
  strong: {
    border: 'border-match-strong/40',
    header: 'bg-match-strong/10 text-match-strong border-b border-match-strong/30',
  },
  good: {
    border: 'border-match-good/40',
    header: 'bg-match-good/10 text-match-good border-b border-match-good/30',
  },
  highway: {
    border: 'border-match-warn/40',
    header: 'bg-match-warn/10 text-match-warn border-b border-match-warn/30',
  },
}

const REFINE_LISTING_TYPES = [
  { value: 'sale', label: 'For Sale' },
  { value: 'pending', label: 'Pending' },
  { value: 'coming_soon', label: 'Coming Soon' },
  { value: 'sold', label: 'Sold' },
  { value: 'rent', label: 'Rent' },
]
const REFINE_BED_OPTIONS = [
  { value: null, label: 'Any' },
  { value: 1, label: '1+' },
  { value: 2, label: '2+' },
  { value: 3, label: '3+' },
  { value: 4, label: '4+' },
]
const REFINE_BATH_OPTIONS = [
  { value: null, label: 'Any' },
  { value: 1, label: '1+' },
  { value: 2, label: '2+' },
  { value: 3, label: '3+' },
]

export default function NewSearch() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { settings: mortgageSettings } = useMortgage()

  const initialZipCodes = (() => {
    const zipsParam = searchParams.get('zips')
    if (!zipsParam) return []
    return zipsParam.split(',').map(z => z.trim()).filter(Boolean)
  })()
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sortBy, setSortBy] = useState('best_match')
  const [visibleCount, setVisibleCount] = useState(50)
  const [collapsedSections, setCollapsedSections] = useState({})
  const [providerErrors, setProviderErrors] = useState([])
  const [progress, setProgress] = useState(null)
  const [searchLog, setSearchLog] = useState([])
  const [foundCount, setFoundCount] = useState(0)
  const [viewMode, setViewMode] = useState('card')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [lastCriteria, setLastCriteria] = useState(null)
  const [refineRadius, setRefineRadius] = useState(25)
  const resultsRef = useRef(null)
  const [liveFilters, setLiveFilters] = useState({
    priceMin: null, priceMax: null,
    bedsMin: null, bathsMin: null,
    listingTypes: [], propertyTypes: [], selectedZips: [],
  })

  // Scroll to top when search starts so progress is visible immediately
  useEffect(() => {
    if (loading) {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [loading])

  const handleSearch = async (criteria, saveName) => {
    setLastCriteria(criteria)
    setRefineRadius(criteria.radius_miles ?? 25)
    setLoading(true)
    setResults(null)
    setProgress(null)
    setSearchLog([])
    setFoundCount(0)
    setProviderErrors([])
    setVisibleCount(50)
    setLiveFilters({ priceMin: null, priceMax: null, bedsMin: null, bathsMin: null, listingTypes: [], propertyTypes: [], selectedZips: [] })

    let partialListings = []

    try {
      await streamSearch(criteria, saveName, {
        onProgress: (msg) => {
          setProgress(msg)
          setSearchLog(prev => {
            const updated = [...prev]
            if (updated.length > 0 && updated[updated.length - 1].status === 'searching') {
              updated[updated.length - 1] = { ...updated[updated.length - 1], status: 'done' }
            }
            return [
              ...updated,
              {
                zip: msg.zip_code || msg.location || `${msg.current}/${msg.total}`,
                location: msg.location,
                status: 'searching',
                count: null,
              },
            ]
          })
          if (msg.found_so_far != null) setFoundCount(msg.found_so_far)
        },
        onPartial: (msg) => {
          partialListings = [...partialListings, ...(msg.listings || [])]
          setFoundCount(partialListings.length)
          setResults({ results: partialListings, total: partialListings.length, provider_errors: [], _partial: true })
        },
        onResults: (msg) => {
          partialListings = []
          setResults(msg)
          setFoundCount(msg.total || 0)
          setProviderErrors(msg.provider_errors || [])
          setProgress(null)
          setSearchLog(prev => {
            if (prev.length === 0) return prev
            const updated = [...prev]
            updated[updated.length - 1] = { ...updated[updated.length - 1], status: 'done' }
            return updated
          })
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

  const resetToNewSearch = () => {
    setResults(null)
    setSearchLog([])
    setProgress(null)
    setLastCriteria(null)
    setLiveFilters({ priceMin: null, priceMax: null, bedsMin: null, bathsMin: null, listingTypes: [], propertyTypes: [], selectedZips: [] })
  }

  const toggleSection = (key) => setCollapsedSections(prev => ({ ...prev, [key]: !prev[key] }))

  const groupResults = (listings) => {
    if (!listings || listings.length === 0) return []
    const sections = [
      { key: 'perfect', icon: '⭐', title: 'Perfect Match', filter: (l) => l.is_gold_star && !l.near_highway, defaultOpen: true },
      { key: 'strong',  icon: '✓',  title: 'Strong Match',  filter: (l) => !l.near_highway && l.match_score >= 3, defaultOpen: true },
      { key: 'good',    icon: '🏠', title: 'Good Options',   filter: (l) => !l.near_highway, defaultOpen: true },
      { key: 'highway', icon: '⚠️', title: 'Near Highway',   filter: (l) => l.near_highway, defaultOpen: false },
    ]
    const assigned = new Set()
    return sections.map(section => {
      const items = listings.filter(l => {
        if (assigned.has(l)) return false
        if (section.filter(l)) { assigned.add(l); return true }
        return false
      })
      return { ...section, items }
    }).filter(s => s.items.length > 0)
  }

  const sortedResults = (list) => {
    if (!list || list.length === 0) return []
    const sorted = [...list]
    const perfectScore = Math.max(...sorted.map(r => r.match_score || 0), 0)
    switch (sortBy) {
      case 'best_match': return sorted.sort((a, b) => {
        const aGold = (a.match_score || 0) >= perfectScore && perfectScore > 0 ? 1 : 0
        const bGold = (b.match_score || 0) >= perfectScore && perfectScore > 0 ? 1 : 0
        if (bGold !== aGold) return bGold - aGold
        if ((b.match_score || 0) !== (a.match_score || 0)) return (b.match_score || 0) - (a.match_score || 0)
        return (a.price || 0) - (b.price || 0)
      })
      case 'price_asc':  return sorted.sort((a, b) => (a.price || 0) - (b.price || 0))
      case 'price_desc': return sorted.sort((a, b) => (b.price || 0) - (a.price || 0))
      case 'sqft_desc':  return sorted.sort((a, b) => (b.sqft || 0) - (a.sqft || 0))
      case 'newest':     return sorted.sort((a, b) => (b.year_built || 0) - (a.year_built || 0))
      default: return sorted
    }
  }

  const applyLiveFilters = (listings) => {
    if (!listings) return []
    return listings.filter(l => {
      if (liveFilters.priceMin && l.price && l.price < liveFilters.priceMin) return false
      if (liveFilters.priceMax && l.price && l.price > liveFilters.priceMax) return false
      if (liveFilters.bedsMin && l.bedrooms && l.bedrooms < liveFilters.bedsMin) return false
      if (liveFilters.bathsMin && l.bathrooms && l.bathrooms < liveFilters.bathsMin) return false
      if (liveFilters.listingTypes?.length > 0 && !liveFilters.listingTypes.includes(l.listing_type)) return false
      if (liveFilters.selectedZips?.length > 0 && !liveFilters.selectedZips.includes(l.zip_code)) return false
      return true
    })
  }

  const filteredListings = applyLiveFilters(results?.results)

  const availableZips = (() => {
    if (!results?.results) return []
    const map = {}
    for (const l of results.results) {
      const zip = l.zip_code
      if (!zip) continue
      if (!map[zip]) map[zip] = { zip, city: l.city || '', count: 0 }
      map[zip].count++
    }
    return Object.values(map).sort((a, b) => b.count - a.count)
  })()

  const hasActiveRefineFilters = liveFilters.priceMin || liveFilters.priceMax ||
    liveFilters.bedsMin || liveFilters.bathsMin ||
    (liveFilters.listingTypes?.length > 0) ||
    (liveFilters.selectedZips?.length > 0)

  const refinePill = (active) =>
    `px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors cursor-pointer ` +
    (active
      ? 'bg-amber-500/20 border-amber-500 text-amber-400'
      : 'bg-canvas-800 border-canvas-600 text-ink-secondary hover:border-canvas-500 hover:text-ink-primary')

  const refineLabelCls = 'text-xs text-ink-muted uppercase tracking-widest font-medium mb-1.5'

  const toggleRefineLT = (val) => {
    const types = liveFilters.listingTypes || []
    const next = types.includes(val) ? types.filter(t => t !== val) : [...types, val]
    setLiveFilters(f => ({ ...f, listingTypes: next }))
  }

  const showRightPanel = loading || results

  return (
    <div className="flex gap-0 items-start relative">
      {/* Sidebar */}
      <div className={`shrink-0 transition-all duration-300 overflow-hidden ${
        showRightPanel
          ? sidebarOpen ? 'w-full lg:w-80 mr-6' : 'w-0 lg:w-0 mr-0'
          : 'w-full max-w-2xl mx-auto'
      }`}>
        <div className={`${showRightPanel ? 'lg:sticky lg:top-24' : ''} ${sidebarOpen ? '' : 'opacity-0 pointer-events-none'}`}>
          {showRightPanel ? (
            /* === REFINE PANEL === */
            <div className="bg-canvas-900 border border-canvas-700 rounded-xl overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-canvas-700">
                <div className="min-w-0">
                  <p className="text-xs text-ink-muted uppercase tracking-widest font-medium">Refine</p>
                  <p className="text-sm text-ink-primary font-medium truncate">{lastCriteria?.location}</p>
                  {lastCriteria?.radius_miles && (
                    <p className="text-xs text-ink-muted">{lastCriteria.radius_miles} mi radius</p>
                  )}
                </div>
                <button
                  onClick={resetToNewSearch}
                  className="shrink-0 ml-3 text-xs border border-canvas-600 text-ink-secondary hover:border-amber-500 hover:text-amber-400 rounded-lg px-3 py-1.5 transition-colors"
                >
                  New Search
                </button>
              </div>

              <div className="px-4 py-3 space-y-3">
                {/* Status */}
                <div>
                  <p className={refineLabelCls}>Status</p>
                  <div className="flex flex-wrap gap-1">
                    {REFINE_LISTING_TYPES.map(t => (
                      <button key={t.value} onClick={() => toggleRefineLT(t.value)} className={refinePill((liveFilters.listingTypes || []).includes(t.value))}>
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Price */}
                <div>
                  <p className={refineLabelCls}>Price</p>
                  <PriceRangeSlider
                    minVal={liveFilters.priceMin}
                    maxVal={liveFilters.priceMax}
                    onMinChange={(v) => setLiveFilters(f => ({ ...f, priceMin: v }))}
                    onMaxChange={(v) => setLiveFilters(f => ({ ...f, priceMax: v }))}
                  />
                </div>

                {/* Beds */}
                <div>
                  <p className={refineLabelCls}>Beds</p>
                  <div className="flex gap-1 flex-wrap">
                    {REFINE_BED_OPTIONS.map(o => (
                      <button key={String(o.value)} onClick={() => setLiveFilters(f => ({ ...f, bedsMin: o.value }))} className={refinePill(liveFilters.bedsMin === o.value)}>
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Baths */}
                <div>
                  <p className={refineLabelCls}>Baths</p>
                  <div className="flex gap-1 flex-wrap">
                    {REFINE_BATH_OPTIONS.map(o => (
                      <button key={String(o.value)} onClick={() => setLiveFilters(f => ({ ...f, bathsMin: o.value }))} className={refinePill(liveFilters.bathsMin === o.value)}>
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Radius */}
                {lastCriteria && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <p className={refineLabelCls}>Radius</p>
                      <span className="text-xs text-amber-400 font-medium">{refineRadius} mi</span>
                    </div>
                    <input
                      type="range"
                      min={5}
                      max={100}
                      step={5}
                      value={refineRadius}
                      onChange={(e) => setRefineRadius(Number(e.target.value))}
                      className="w-full h-1.5 rounded-full appearance-none cursor-pointer accent-amber-500"
                    />
                    <div className="flex justify-between text-xs text-ink-muted mt-1">
                      <span>5 mi</span><span>100 mi</span>
                    </div>
                    {refineRadius !== (lastCriteria?.radius_miles ?? 25) && (
                      <button
                        onClick={() => handleSearch({ ...lastCriteria, radius_miles: refineRadius }, null)}
                        className="mt-2 w-full text-xs bg-amber-500/20 border border-amber-500 text-amber-400 hover:bg-amber-500/30 rounded-lg py-1.5 transition-colors font-medium"
                      >
                        Re-search ({refineRadius} mi)
                      </button>
                    )}
                  </div>
                )}

                {/* Areas */}
                {availableZips.length > 1 && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-xs text-ink-muted uppercase tracking-widest font-medium">Areas</p>
                      {(liveFilters.selectedZips || []).length > 0 && (
                        <button onClick={() => setLiveFilters(f => ({ ...f, selectedZips: [] }))} className="text-xs text-amber-400 hover:text-amber-300">
                          Show all
                        </button>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {availableZips.map(({ zip, city, count }) => {
                        const active = !(liveFilters.selectedZips?.length > 0) || liveFilters.selectedZips.includes(zip)
                        const toggle = () => {
                          const current = liveFilters.selectedZips || []
                          let next
                          if (current.length === 0) next = [zip]
                          else if (current.includes(zip)) {
                            next = current.filter(z => z !== zip)
                            if (next.length === availableZips.length) next = []
                          } else {
                            next = [...current, zip]
                            if (next.length === availableZips.length) next = []
                          }
                          setLiveFilters(f => ({ ...f, selectedZips: next }))
                        }
                        return (
                          <button
                            key={zip}
                            onClick={toggle}
                            className={`px-2 py-0.5 rounded-lg text-xs font-medium border transition-colors ${
                              active
                                ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                                : 'bg-canvas-800 border-canvas-600 text-ink-muted opacity-50 hover:opacity-80'
                            }`}
                          >
                            {city || zip} <span className="opacity-60">({count})</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Clear filters */}
                {hasActiveRefineFilters && (
                  <button
                    onClick={() => setLiveFilters({ priceMin: null, priceMax: null, bedsMin: null, bathsMin: null, listingTypes: [], propertyTypes: [], selectedZips: [] })}
                    className="w-full flex items-center justify-center gap-1 text-xs text-ink-muted hover:text-amber-400 border border-canvas-600 hover:border-amber-500/50 rounded-lg py-1.5 transition-colors"
                  >
                    <X size={11} />Clear filters
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* === SEARCH FORM === */
            <>
              <h1 className="font-serif text-3xl text-ink-primary mb-4">Find Your Home</h1>
              <SearchForm onSearch={handleSearch} onLoading={setLoading} initialZipCodes={initialZipCodes} />
            </>
          )}
        </div>
      </div>

      {/* Collapse toggle — only shown when results are visible */}
      {showRightPanel && (
        <button
          onClick={() => setSidebarOpen(p => !p)}
          className="hidden lg:flex shrink-0 items-center justify-center w-6 h-12 self-start mt-1 mr-2 rounded-md bg-canvas-800 border border-canvas-600 text-ink-muted hover:text-amber-400 hover:border-amber-500 transition-colors"
          title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {sidebarOpen ? '‹' : '›'}
        </button>
      )}

      {/* Right: Progress + Results */}
      {showRightPanel && (
        <div className="flex-1 min-w-0" ref={resultsRef}>
          {/* Terminal progress */}
          {(loading || searchLog.length > 0) && (
            <div className="mb-6">
              <SearchProgressTerminal
                progress={progress}
                searchLog={searchLog}
                foundCount={foundCount}
              />
            </div>
          )}

          {/* Provider errors */}
          {providerErrors.length > 0 && !loading && (
            <div className="bg-match-warn/10 border border-match-warn/30 rounded-xl p-4 mb-4">
              <p className="text-sm text-match-warn font-medium mb-1">Some providers had issues:</p>
              <ul className="text-sm text-match-warn/80 list-disc list-inside">
                {providerErrors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}

          {/* Results */}
          {results && (results.total > 0 || !loading) && (
            <div>
              {/* Results header */}
              <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
                <div>
                  <span className="font-mono text-2xl text-amber-400 font-medium">{filteredListings.length}</span>
                  <span className="text-ink-secondary text-sm ml-2">
                    {loading ? 'properties found so far…' : 'properties found'}
                  </span>
                  {results?.total > filteredListings.length && !loading && (
                    <span className="text-ink-muted text-xs ml-2">({results.total} total before filters)</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {!loading && (
                    <div className="flex items-center border border-canvas-600 rounded-lg overflow-hidden">
                      <button
                        onClick={() => setViewMode('card')}
                        className={`p-1.5 transition-colors ${viewMode === 'card' ? 'bg-canvas-700 text-amber-400' : 'text-ink-muted hover:text-ink-primary'}`}
                        title="Card view"
                      >
                        <LayoutList size={15} />
                      </button>
                      <button
                        onClick={() => setViewMode('thumbnail')}
                        className={`p-1.5 transition-colors ${viewMode === 'thumbnail' ? 'bg-canvas-700 text-amber-400' : 'text-ink-muted hover:text-ink-primary'}`}
                        title="Thumbnail view"
                      >
                        <LayoutGrid size={15} />
                      </button>
                    </div>
                  )}
                  {!loading && viewMode === 'card' && (
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value)}
                      className="bg-canvas-800 border border-canvas-600 text-ink-secondary rounded-lg py-1.5 px-3 text-sm focus:border-amber-500 focus:outline-none"
                    >
                      <option value="best_match">Best Match</option>
                      <option value="price_asc">Price: Low to High</option>
                      <option value="price_desc">Price: High to Low</option>
                      <option value="sqft_desc">Largest First</option>
                      <option value="newest">Newest Built</option>
                    </select>
                  )}
                </div>
              </div>

              {filteredListings.length === 0 ? (
                <div className="text-center py-16 bg-canvas-900 rounded-xl border border-canvas-700">
                  <p className="text-ink-secondary text-lg mb-2">No properties match your filters</p>
                  <p className="text-ink-muted text-sm">Try adjusting the refine panel on the left</p>
                </div>
              ) : viewMode === 'thumbnail' ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
                  {filteredListings.map((listing, i) => (
                    <div key={`${listing.source}-${listing.source_id}-${i}`} className="card-stream-enter">
                      <ThumbnailCard listing={listing} />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-5">
                  {groupResults(sortedResults(filteredListings)).map(section => {
                    const styles = SECTION_STYLES[section.key] || SECTION_STYLES.good
                    const isCollapsed = collapsedSections[section.key] ?? !section.defaultOpen
                    return (
                      <div key={section.key} className={`border rounded-xl overflow-hidden ${styles.border} bg-canvas-900`}>
                        <button
                          onClick={() => toggleSection(section.key)}
                          className={`w-full flex items-center justify-between px-5 py-3 font-sans font-semibold text-sm ${styles.header}`}
                        >
                          <span>{section.icon} {section.title} ({section.items.length})</span>
                          <span className="text-xs opacity-70">{isCollapsed ? '+ Show' : '− Hide'}</span>
                        </button>
                        {!isCollapsed && (
                          <div className="p-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
                              {section.items.slice(0, visibleCount).map((listing, i) => (
                                <div key={`${listing.source}-${listing.source_id}-${i}`} className="card-stream-enter">
                                  <PropertyCard listing={listing} isGoldStar={listing.is_gold_star} mortgageSettings={mortgageSettings.enabled ? mortgageSettings : null} />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
