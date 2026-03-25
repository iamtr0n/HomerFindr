import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useMemo } from 'react'
import { api } from '../api'
import { Play, Trash2, Clock, MapPin, DollarSign, Loader2, Mail, Search, Home, TrendingUp } from 'lucide-react'
import { Card, CardHeader, CardContent } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import PropertyCard from '../components/PropertyCard'

export default function Dashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['searches'],
    queryFn: api.listSearches,
  })

  const searches = data?.searches || []

  // Find the most recently run search for "Recent Activity"
  const recentSearch = useMemo(() => {
    const withRun = searches.filter(s => s.last_run_at)
    if (withRun.length === 0) return null
    return withRun.sort((a, b) => new Date(b.last_run_at) - new Date(a.last_run_at))[0]
  }, [searches])

  const { data: recentData } = useQuery({
    queryKey: ['recent-results', recentSearch?.id],
    queryFn: () => api.getResults(recentSearch.id),
    enabled: !!recentSearch?.id,
  })

  const recentResults = (recentData?.results || []).slice(0, 4)

  // Stats
  const totalSearches = searches.length
  const totalProperties = searches.reduce((sum, s) => sum + (s.result_count || 0), 0)
  const activeSearches = searches.filter(s => s.is_active).length

  const runMutation = useMutation({
    mutationFn: (id) => api.runSearch(id),
    onSuccess: (data, id) => {
      queryClient.invalidateQueries({ queryKey: ['searches'] })
      navigate(`/search/${id}/results`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.deleteSearch(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['searches'] }),
  })

  const reportMutation = useMutation({
    mutationFn: () => api.sendReport(),
  })

  return (
    <div>
      {/* Page header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-900">HomerFindr</h1>
        <Button
          variant="secondary"
          onClick={() => reportMutation.mutate()}
          disabled={reportMutation.isPending}
        >
          {reportMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Mail size={16} />}
          Send Report
        </Button>
      </div>

      {/* Stat Header */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-brand-50 rounded-lg">
              <Search size={20} className="text-brand-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{totalSearches}</p>
              <p className="text-sm text-slate-500">Saved Searches</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-brand-50 rounded-lg">
              <Home size={20} className="text-brand-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{totalProperties}</p>
              <p className="text-sm text-slate-500">Properties Found</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-brand-50 rounded-lg">
              <TrendingUp size={20} className="text-brand-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{activeSearches}</p>
              <p className="text-sm text-slate-500">Active Searches</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Saved Searches section */}
      <h2 className="text-lg font-semibold text-slate-800 mb-4">Saved Searches</h2>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={32} className="animate-spin text-brand-500" />
        </div>
      ) : searches.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-lg shadow">
          <p className="text-slate-500 text-lg mb-4">No saved searches yet</p>
          <Button variant="default" onClick={() => navigate('/search/new')}>
            Create Your First Search
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {searches.map((s) => {
            const c = s.criteria
            const priceRange = (c.price_min || c.price_max)
              ? `$${(c.price_min || 0).toLocaleString()} – $${(c.price_max || '∞').toLocaleString()}`
              : 'Any price'

            return (
              <Card key={s.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="p-4 pb-2">
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold text-slate-800 text-base leading-tight">{s.name}</h3>
                    <Badge variant={s.is_active ? 'success' : 'secondary'}>
                      {s.is_active ? 'Active' : 'Paused'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-2">
                  <div className="space-y-1 text-sm text-slate-600 mb-3">
                    <p className="flex items-center gap-1.5">
                      <MapPin size={14} /> {c.location || 'No location'}
                      {c.radius_miles && <span className="text-slate-400">({c.radius_miles}mi)</span>}
                    </p>
                    <p className="flex items-center gap-1.5">
                      <DollarSign size={14} /> {priceRange}
                    </p>
                    <p className="text-xs text-slate-400 flex items-center gap-1.5">
                      <Clock size={12} />
                      {s.last_run_at ? `Last run: ${new Date(s.last_run_at).toLocaleString()}` : 'Never run'}
                    </p>
                    {(c.bedrooms_min || c.bathrooms_min || c.sqft_min) && (
                      <p className="text-xs text-slate-500">
                        {c.bedrooms_min && `${c.bedrooms_min}+ bed`}
                        {c.bathrooms_min && ` · ${c.bathrooms_min}+ bath`}
                        {c.sqft_min && ` · ${c.sqft_min.toLocaleString()}+ sqft`}
                      </p>
                    )}
                    {s.result_count != null && (
                      <p className="text-xs text-brand-600 font-medium">{s.result_count} properties</p>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="default"
                      size="sm"
                      className="flex-1"
                      onClick={() => runMutation.mutate(s.id)}
                      disabled={runMutation.isPending}
                    >
                      {runMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                      Run Now
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate(`/search/${s.id}/results`)}
                    >
                      Results
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        if (confirm(`Delete "${s.name}"?`)) deleteMutation.mutate(s.id)
                      }}
                    >
                      <Trash2 size={16} className="text-red-500" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Recent Activity */}
      {recentSearch && recentResults.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">
            Recent Results from "{recentSearch.name}"
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {recentResults.map((listing, i) => (
              <PropertyCard key={`${listing.source}-${listing.source_id}-${i}`} listing={listing} />
            ))}
          </div>
        </div>
      )}

      {reportMutation.isSuccess && (
        <div className="fixed bottom-4 right-4 bg-brand-600 text-white px-4 py-2 rounded-lg shadow-lg">
          Report sent!
        </div>
      )}
    </div>
  )
}
