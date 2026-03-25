import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api'
import PropertyCard from '../components/PropertyCard'
import { ArrowLeft, Play, Loader2, Filter } from 'lucide-react'
import { useState } from 'react'

export default function SearchResults() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [showNewOnly, setShowNewOnly] = useState(false)
  const [sortBy, setSortBy] = useState('price_asc')

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
    onSuccess: () => {
      resultsQuery.refetch()
      searchQuery.refetch()
    },
  })

  const search = searchQuery.data
  const results = resultsQuery.data?.results || []

  const sortedResults = () => {
    const list = [...results]
    switch (sortBy) {
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
        <button onClick={() => navigate('/')} className="text-gray-500 hover:text-gray-800">
          <ArrowLeft size={24} />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-800">
            {search?.name || 'Search Results'}
          </h1>
          {search?.criteria?.location && (
            <p className="text-sm text-gray-500">
              {search.criteria.location}
              {search.criteria.radius_miles && ` (${search.criteria.radius_miles}mi radius)`}
            </p>
          )}
        </div>
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {runMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          Refresh
        </button>
      </div>

      {/* Filters bar */}
      <div className="flex items-center gap-4 mb-4 bg-white p-3 rounded-lg shadow-sm">
        <Filter size={16} className="text-gray-400" />
        <button
          onClick={() => setShowNewOnly(!showNewOnly)}
          className={`text-sm px-3 py-1 rounded-full border ${
            showNewOnly ? 'bg-green-100 border-green-300 text-green-700' : 'border-gray-200'
          }`}
        >
          New only
        </button>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="ml-auto py-1.5 px-3 border rounded-lg text-sm"
        >
          <option value="price_asc">Price: Low to High</option>
          <option value="price_desc">Price: High to Low</option>
          <option value="sqft_desc">Largest First</option>
          <option value="newest">Newest Built</option>
        </select>
        <span className="text-sm text-gray-500">{results.length} results</span>
      </div>

      {/* Results grid */}
      {resultsQuery.isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={32} className="animate-spin text-blue-500" />
        </div>
      ) : results.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <p className="text-gray-500 text-lg mb-4">
            {showNewOnly ? 'No new listings since last check' : 'No cached results'}
          </p>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Run Search Now
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {sortedResults().map((listing, i) => (
            <PropertyCard key={`${listing.source}-${listing.source_id}-${i}`} listing={listing} />
          ))}
        </div>
      )}
    </div>
  )
}
