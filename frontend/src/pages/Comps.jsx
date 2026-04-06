import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { api } from '../api'
import PropertyCard from '../components/PropertyCard'

export default function Comps() {
  const { listingId } = useParams()
  const navigate = useNavigate()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['comps', listingId],
    queryFn: () => api.getComps(listingId),
  })

  const comps = data?.comps ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm text-ink-secondary hover:text-ink-primary transition-colors"
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <h1 className="text-xl font-semibold text-ink-primary">Comparable Sales</h1>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-ink-muted py-8 justify-center">
          <Loader2 size={16} className="animate-spin" />
          Searching for comparable sales nearby…
        </div>
      )}

      {isError && (
        <p className="text-sm text-red-400 py-4">Failed to load comparable sales. Please try again.</p>
      )}

      {!isLoading && !isError && comps.length === 0 && (
        <p className="text-sm text-ink-muted py-8 text-center">No comparable sales found in this area.</p>
      )}

      {comps.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {comps.map((comp, i) => (
            <PropertyCard key={comp.source_id || i} listing={comp} />
          ))}
        </div>
      )}
    </div>
  )
}
