import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Play, Trash2, Clock, MapPin, DollarSign, Loader2, Mail } from 'lucide-react'

export default function Dashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['searches'],
    queryFn: api.listSearches,
  })

  const runMutation = useMutation({
    mutationFn: (id) => api.runSearch(id),
    onSuccess: (data, id) => {
      queryClient.invalidateQueries(['searches'])
      navigate(`/search/${id}/results`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.deleteSearch(id),
    onSuccess: () => queryClient.invalidateQueries(['searches']),
  })

  const reportMutation = useMutation({
    mutationFn: () => api.sendReport(),
  })

  const searches = data?.searches || []

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Saved Searches</h1>
        <button
          onClick={() => reportMutation.mutate()}
          disabled={reportMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 text-sm"
        >
          {reportMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Mail size={16} />}
          Send Report
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={32} className="animate-spin text-blue-500" />
        </div>
      ) : searches.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <p className="text-gray-500 text-lg mb-4">No saved searches yet</p>
          <button
            onClick={() => navigate('/search/new')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Create Your First Search
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {searches.map((s) => {
            const c = s.criteria
            const priceRange = (c.price_min || c.price_max)
              ? `$${(c.price_min || 0).toLocaleString()} - $${(c.price_max || '∞').toLocaleString()}`
              : 'Any price'

            return (
              <div key={s.id} className="bg-white rounded-lg shadow-md p-5 hover:shadow-lg transition-shadow">
                <div className="flex justify-between items-start mb-3">
                  <h3 className="font-semibold text-gray-800 text-lg">{s.name}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                  }`}>
                    {s.is_active ? 'Active' : 'Paused'}
                  </span>
                </div>

                <div className="space-y-1 text-sm text-gray-600 mb-4">
                  <p className="flex items-center gap-1.5">
                    <MapPin size={14} /> {c.location || 'No location'}
                    {c.radius_miles && <span className="text-gray-400">({c.radius_miles}mi)</span>}
                  </p>
                  <p className="flex items-center gap-1.5">
                    <DollarSign size={14} /> {priceRange}
                  </p>
                  <p className="text-xs text-gray-400 flex items-center gap-1.5">
                    <Clock size={12} />
                    {s.last_run_at ? `Last run: ${new Date(s.last_run_at).toLocaleString()}` : 'Never run'}
                  </p>
                  {(c.bedrooms_min || c.bathrooms_min || c.sqft_min) && (
                    <p className="text-xs text-gray-500">
                      {c.bedrooms_min && `${c.bedrooms_min}+ bed`}
                      {c.bathrooms_min && ` · ${c.bathrooms_min}+ bath`}
                      {c.sqft_min && ` · ${c.sqft_min.toLocaleString()}+ sqft`}
                    </p>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => runMutation.mutate(s.id)}
                    disabled={runMutation.isPending}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
                  >
                    {runMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                    Run Now
                  </button>
                  <button
                    onClick={() => navigate(`/search/${s.id}/results`)}
                    className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
                  >
                    Results
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete "${s.name}"?`)) deleteMutation.mutate(s.id)
                    }}
                    className="px-3 py-2 text-red-500 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {reportMutation.isSuccess && (
        <div className="fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg">
          Report sent!
        </div>
      )}
    </div>
  )
}
