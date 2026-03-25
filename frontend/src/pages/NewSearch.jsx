import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SearchForm from '../components/SearchForm'
import PropertyCard from '../components/PropertyCard'
import { Loader2 } from 'lucide-react'

export default function NewSearch() {
  const navigate = useNavigate()
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sortBy, setSortBy] = useState('price_asc')

  const handleResults = (data) => {
    setResults(data)
    if (data.search_id) {
      // Was saved - could navigate to results page
    }
  }

  const sortedResults = () => {
    if (!results?.results) return []
    const list = [...results.results]
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
      <h1 className="text-2xl font-bold text-gray-800 mb-6">New Search</h1>

      <SearchForm onResults={handleResults} onLoading={setLoading} />

      {loading && (
        <div className="flex items-center justify-center gap-3 py-12 text-blue-600">
          <Loader2 size={24} className="animate-spin" />
          <span className="text-lg">Searching across all platforms...</span>
        </div>
      )}

      {results && !loading && (
        <div className="mt-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-800">
              {results.total} Properties Found
              {results.search_name && <span className="text-green-600 text-sm ml-2">(Saved as "{results.search_name}")</span>}
            </h2>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="py-1.5 px-3 border rounded-lg text-sm"
            >
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="sqft_desc">Largest First</option>
              <option value="newest">Newest Built</option>
            </select>
          </div>

          {results.total === 0 ? (
            <p className="text-center text-gray-500 py-8">No properties match your criteria. Try adjusting your filters.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {sortedResults().map((listing, i) => (
                <PropertyCard key={`${listing.source}-${listing.source_id}-${i}`} listing={listing} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
