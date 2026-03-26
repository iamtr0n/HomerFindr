import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SearchForm from '../components/SearchForm'
import PropertyCard from '../components/PropertyCard'
import { Loader2 } from 'lucide-react'
import { streamSearch } from '../api'

export default function NewSearch() {
  const navigate = useNavigate()
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sortBy, setSortBy] = useState('best_match')
  const [visibleCount, setVisibleCount] = useState(50)
  const [collapsedSections, setCollapsedSections] = useState({})
  const [providerErrors, setProviderErrors] = useState([])
  const [progress, setProgress] = useState(null) // { current, total, location }

  const handleSearch = async (criteria, saveName) => {
    setLoading(true)
    setResults(null)
    setProgress(null)
    setProviderErrors([])
    setVisibleCount(50)

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

  const toggleSection = (key) => setCollapsedSections(prev => ({ ...prev, [key]: !prev[key] }))

  const groupResults = (listings) => {
    if (!listings || listings.length === 0) return []

    const sections = [
      {
        key: 'perfect',
        icon: '\u2B50',
        title: 'Perfect Match',
        color: 'bg-yellow-50 border-yellow-300 text-yellow-800',
        headerColor: 'bg-yellow-100',
        filter: (l) => l.is_gold_star && !l.near_highway,
        defaultOpen: true,
      },
      {
        key: 'strong',
        icon: '\u2705',
        title: 'Strong Match',
        color: 'bg-green-50 border-green-300 text-green-800',
        headerColor: 'bg-green-100',
        filter: (l) => !l.near_highway && l.match_score >= 3,
        defaultOpen: true,
      },
      {
        key: 'good',
        icon: '\uD83C\uDFE0',
        title: 'Good Options',
        color: 'bg-blue-50 border-blue-300 text-blue-800',
        headerColor: 'bg-blue-100',
        filter: (l) => !l.near_highway,
        defaultOpen: false,
      },
      {
        key: 'highway',
        icon: '\u26A0\uFE0F',
        title: 'Near Highway',
        color: 'bg-amber-50 border-amber-300 text-amber-800',
        headerColor: 'bg-amber-100',
        filter: (l) => l.near_highway,
        defaultOpen: false,
      },
    ]

    // Assign each listing to the FIRST matching section (waterfall)
    const assigned = new Set()
    const grouped = sections.map(section => {
      const items = listings.filter(l => {
        if (assigned.has(l)) return false
        if (section.filter(l)) {
          assigned.add(l)
          return true
        }
        return false
      })
      return { ...section, items }
    }).filter(s => s.items.length > 0)

    return grouped
  }

  const sortedResults = () => {
    if (!results?.results) return []
    const list = [...results.results]
    const perfectScore = Math.max(...list.map(r => r.match_score || 0), 0)
    switch (sortBy) {
      case 'best_match': return list.sort((a, b) => {
        const aGold = (a.match_score || 0) >= perfectScore && perfectScore > 0 ? 1 : 0
        const bGold = (b.match_score || 0) >= perfectScore && perfectScore > 0 ? 1 : 0
        if (bGold !== aGold) return bGold - aGold
        if ((b.match_score || 0) !== (a.match_score || 0)) return (b.match_score || 0) - (a.match_score || 0)
        return (a.price || 0) - (b.price || 0)
      })
      case 'price_asc': return list.sort((a, b) => (a.price || 0) - (b.price || 0))
      case 'price_desc': return list.sort((a, b) => (b.price || 0) - (a.price || 0))
      case 'sqft_desc': return list.sort((a, b) => (b.sqft || 0) - (a.sqft || 0))
      case 'newest': return list.sort((a, b) => (b.year_built || 0) - (a.year_built || 0))
      default: return list
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">New Search</h1>

      <SearchForm onSearch={handleSearch} onLoading={setLoading} />

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

      {/* Provider error banner */}
      {providerErrors.length > 0 && !loading && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mt-4">
          <p className="text-sm text-amber-800 font-medium">Some providers had issues:</p>
          <ul className="text-sm text-amber-700 mt-1 list-disc list-inside">
            {providerErrors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}

      {results && !loading && (
        <div className="mt-6">
          <button
            onClick={() => setResults(null)}
            className="text-sm text-blue-600 hover:text-blue-800 mb-4"
          >
            &larr; Back to search
          </button>

          <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
            <h2 className="text-lg font-semibold text-slate-800">
              {results.total} Properties Found
              {results.search_name && <span className="text-brand-600 text-sm ml-2">(Saved as "{results.search_name}")</span>}
            </h2>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="py-1.5 px-3 border border-slate-200 rounded-lg text-sm"
            >
              <option value="best_match">Best Match</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="sqft_desc">Largest First</option>
              <option value="newest">Newest Built</option>
            </select>
          </div>

          {results.total === 0 ? (
            <p className="text-center text-slate-500 py-8">No properties match your criteria. Try adjusting your filters.</p>
          ) : (
            <div className="space-y-6">
              {groupResults(sortedResults()).map(section => {
                const isCollapsed = collapsedSections[section.key] ?? !section.defaultOpen
                return (
                  <div key={section.key} className={`border rounded-lg overflow-hidden ${section.color}`}>
                    <button
                      onClick={() => toggleSection(section.key)}
                      className={`w-full flex items-center justify-between px-4 py-3 ${section.headerColor} font-semibold text-sm`}
                    >
                      <span>{section.icon} {section.title} ({section.items.length})</span>
                      <span className="text-xs">{isCollapsed ? '+ Show' : '- Hide'}</span>
                    </button>
                    {!isCollapsed && (
                      <div className="p-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                          {section.items.map((listing, i) => (
                            <PropertyCard
                              key={`${listing.source}-${listing.source_id}-${i}`}
                              listing={listing}
                              isGoldStar={listing.is_gold_star}
                            />
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
  )
}
