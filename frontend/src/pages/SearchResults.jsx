import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api'
import PropertyCard from '../components/PropertyCard'
import { Button } from '../components/ui/Button'
import { ArrowLeft, Play, Loader2, Filter, DollarSign } from 'lucide-react'
import { useState } from 'react'

export default function SearchResults() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [showNewOnly, setShowNewOnly] = useState(false)
  const [sortBy, setSortBy] = useState('match_score')
  const [filterMinPrice, setFilterMinPrice] = useState('')
  const [filterMaxPrice, setFilterMaxPrice] = useState('')
  const [filterMinBeds, setFilterMinBeds] = useState('')
  const [filterMinBaths, setFilterMinBaths] = useState('')
  const [providerErrors, setProviderErrors] = useState([])

  const searchQuery = useQuery({
    queryKey: ['search', id],
    queryFn: () => api.getSearch(id),
  })

  const resultsQuery = useQuery({
    queryKey: ['results', id, showNewOnly],
    queryFn: () => api.getResults(id, showNewOnly),
  })

  const runMutation = useMutation({
    mutationFn: () => api.runSearch(id),
    onSuccess: (data) => {
      setProviderErrors(data.provider_errors || [])
      resultsQuery.refetch()
      searchQuery.refetch()
    },
  })

  const search = searchQuery.data
  const results = resultsQuery.data?.results || []

  const filteredAndSorted = () => {
    let list = [...results]
    // Apply filters
    if (filterMinPrice) list = list.filter(l => (l.price || 0) >= +filterMinPrice)
    if (filterMaxPrice) list = list.filter(l => !l.price || l.price <= +filterMaxPrice)
    if (filterMinBeds) list = list.filter(l => (l.bedrooms || 0) >= +filterMinBeds)
    if (filterMinBaths) list = list.filter(l => (l.bathrooms || 0) >= +filterMinBaths)
    // Apply sort
    switch (sortBy) {
      case 'match_score': return list.sort((a, b) => {
        const scoreDiff = (b.match_score || 0) - (a.match_score || 0)
        if (scoreDiff !== 0) return scoreDiff
        return (b.is_gold_star ? 1 : 0) - (a.is_gold_star ? 1 : 0)
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
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate('/')} className="text-slate-500 hover:text-slate-800">
          <ArrowLeft size={24} />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-800">
            {search?.name || 'Search Results'}
          </h1>
          {search?.criteria?.location && (
            <p className="text-sm text-slate-500">
              {search.criteria.location}
              {search.criteria.radius_miles && ` (${search.criteria.radius_miles}mi radius)`}
            </p>
          )}
        </div>
        <Button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          variant="default"
        >
          {runMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          Refresh
        </Button>
      </div>

      {/* Provider error banner */}
      {providerErrors.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
          <p className="text-sm text-amber-800 font-medium">Some providers had issues:</p>
          <ul className="text-sm text-amber-700 mt-1 list-disc list-inside">
            {providerErrors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}

      {/* Filters bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4 bg-white p-3 rounded-lg shadow-sm">
        <Filter size={16} className="text-slate-400" />

        {/* New Only toggle */}
        <button
          onClick={() => setShowNewOnly(!showNewOnly)}
          className={`text-sm px-3 py-1 rounded-full border ${
            showNewOnly ? 'bg-brand-100 border-brand-300 text-brand-700' : 'border-slate-200 text-slate-600'
          }`}
        >
          New only
        </button>

        {/* Price range inputs */}
        <div className="flex items-center gap-1">
          <DollarSign size={14} className="text-slate-400" />
          <input
            type="number"
            placeholder="Min price"
            value={filterMinPrice}
            onChange={(e) => setFilterMinPrice(e.target.value)}
            className="w-28 py-1 px-2 border border-slate-200 rounded text-sm"
          />
          <span className="text-slate-400">-</span>
          <input
            type="number"
            placeholder="Max price"
            value={filterMaxPrice}
            onChange={(e) => setFilterMaxPrice(e.target.value)}
            className="w-28 py-1 px-2 border border-slate-200 rounded text-sm"
          />
        </div>

        {/* Beds filter */}
        <select
          value={filterMinBeds}
          onChange={(e) => setFilterMinBeds(e.target.value)}
          className="py-1 px-2 border border-slate-200 rounded text-sm text-slate-600"
        >
          <option value="">Beds</option>
          <option value="1">1+ bed</option>
          <option value="2">2+ beds</option>
          <option value="3">3+ beds</option>
          <option value="4">4+ beds</option>
          <option value="5">5+ beds</option>
        </select>

        {/* Baths filter */}
        <select
          value={filterMinBaths}
          onChange={(e) => setFilterMinBaths(e.target.value)}
          className="py-1 px-2 border border-slate-200 rounded text-sm text-slate-600"
        >
          <option value="">Baths</option>
          <option value="1">1+ bath</option>
          <option value="2">2+ baths</option>
          <option value="3">3+ baths</option>
        </select>

        {/* Sort dropdown */}
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="ml-auto py-1.5 px-3 border border-slate-200 rounded-lg text-sm text-slate-600"
        >
          <option value="match_score">Best Match</option>
          <option value="price_asc">Price: Low to High</option>
          <option value="price_desc">Price: High to Low</option>
          <option value="sqft_desc">Largest First</option>
          <option value="newest">Newest Built</option>
        </select>

        {/* Result count */}
        <span className="text-sm text-slate-500">
          {filteredAndSorted().length} of {results.length} results
        </span>
      </div>

      {/* Results grid */}
      {resultsQuery.isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={32} className="animate-spin text-brand-500" />
        </div>
      ) : results.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <p className="text-slate-500 text-lg mb-4">
            {showNewOnly ? 'No new listings since last check' : 'No cached results'}
          </p>
          <Button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            variant="default"
          >
            Run Search Now
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredAndSorted().map((listing, i) => (
            <PropertyCard key={`${listing.source}-${listing.source_id}-${i}`} listing={listing} />
          ))}
        </div>
      )}
    </div>
  )
}
