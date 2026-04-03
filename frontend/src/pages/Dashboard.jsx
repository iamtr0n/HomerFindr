import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useMemo, useState, useEffect, useCallback } from 'react'
import { api, getSessionId, setSessionId } from '../api'
import { Play, Trash2, Clock, MapPin, DollarSign, Loader2, Home, Bell, BellOff, Save, Bookmark, Settings2, X, Plus, QrCode, ChevronDown, ChevronUp, Pencil } from 'lucide-react'
import { estimateCommute } from '../utils/commute'
import { QRCodeSVG } from 'qrcode.react'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import PropertyCard from '../components/PropertyCard'
import { useMortgage } from '../components/MortgageBar'
import SearchForm from '../components/SearchForm'


export default function Dashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['searches'], queryFn: api.listSearches })
  const searches = data?.searches || []

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

  // recentResults computed below after starredSourceIds is available
  const totalSearches = searches.length
  const totalProperties = searches.reduce((sum, s) => sum + (s.result_count || 0), 0)
  const activeSearches = searches.filter(s => s.is_active).length

  const starredQuery = useQuery({ queryKey: ['starred'], queryFn: api.getStarredListings })
  const starredListings = starredQuery.data?.listings || []

  const allListingsQuery = useQuery({ queryKey: ['all-listings'], queryFn: api.getAllListings })
  const dismissedQuery = useQuery({ queryKey: ['dismissed'], queryFn: api.getDismissed })
  const dismissedIds = useMemo(() => new Set(dismissedQuery.data?.dismissed || []), [dismissedQuery.data])

  const dismissMutation = useMutation({
    mutationFn: (sourceId) => api.dismissListing(sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dismissed'] }),
  })
  const undismissMutation = useMutation({
    mutationFn: (sourceId) => api.undismissListing(sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dismissed'] }),
  })
  const handleDismiss = useCallback((sourceId) => { dismissMutation.mutate(sourceId) }, [dismissMutation])

  const allListings = useMemo(() => {
    const raw = allListingsQuery.data?.results || []
    const seen = new Set()
    return raw.filter(l => {
      if (dismissedIds.has(l.source_id)) return false
      if (seen.has(l.source_id)) return false
      seen.add(l.source_id)
      return true
    })
  }, [allListingsQuery.data, dismissedIds])

  const dismissedListings = useMemo(() => {
    const raw = allListingsQuery.data?.results || []
    const seen = new Set()
    return raw.filter(l => {
      if (!dismissedIds.has(l.source_id)) return false
      if (seen.has(l.source_id)) return false
      seen.add(l.source_id)
      return true
    })
  }, [allListingsQuery.data, dismissedIds])

  // Deduplicate sections — each listing appears in exactly one section by priority: New > Saved > All
  const starredSourceIds = useMemo(() => new Set(starredListings.map(l => l.source_id)), [starredListings])
  const filteredStarred = useMemo(() => starredListings.filter(l => !l.is_new), [starredListings])
  const unsectionedListings = useMemo(
    () => allListings.filter(l => !l.is_new && !starredSourceIds.has(l.source_id)),
    [allListings, starredSourceIds]
  )
  const recentResults = useMemo(
    () => (recentData?.results || []).filter(l => !l.is_new && !starredSourceIds.has(l.source_id)).slice(0, 4),
    [recentData, starredSourceIds]
  )

  // Session
  const [sessionCode, setSessionCode] = useState(getSessionId)
  const [manualCode, setManualCode] = useState('')
  const [sessionError, setSessionError] = useState('')

  useEffect(() => {
    // Initialize session on first load — server returns existing code or migrates 'default' data
    api.initSession().then(({ session_id }) => {
      if (session_id && session_id !== sessionCode) {
        setSessionId(session_id)
        setSessionCode(session_id)
        // Refetch all data with the new session
        queryClient.invalidateQueries()
      }
    }).catch(() => {})
  }, [])

  const applySessionCode = useCallback((code) => {
    const clean = code.trim().toUpperCase()
    if (!/^[A-Z0-9]{6}$/.test(clean)) {
      setSessionError('Enter a valid 6-character code')
      return
    }
    setSessionId(clean)
    setSessionCode(clean)
    setManualCode('')
    setSessionError('')
    // Re-init with the new code so the server registers it, then reload all data
    api.initSession().then(() => queryClient.invalidateQueries())
  }, [queryClient])

  // QR connect
  const [showQr, setShowQr] = useState(false)
  const networkQuery = useQuery({ queryKey: ['network-info'], queryFn: api.getNetworkInfo, staleTime: Infinity })
  const appUrl = networkQuery.data?.url || window.location.origin

  // Push notifications
  const [pushEnabled, setPushEnabled] = useState(false)
  const [pushLoading, setPushLoading] = useState(false)

  useEffect(() => {
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      navigator.serviceWorker.ready.then(reg => reg.pushManager.getSubscription()).then(sub => {
        setPushEnabled(!!sub)
      }).catch(() => {})
    }
  }, [])

  const togglePush = useCallback(async () => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      alert('Push notifications are not supported in this browser.')
      return
    }
    setPushLoading(true)
    try {
      const reg = await navigator.serviceWorker.ready
      if (pushEnabled) {
        const sub = await reg.pushManager.getSubscription()
        if (sub) {
          const id = btoa(sub.endpoint).slice(0, 32)
          await api.unsubscribePush(id)
          await sub.unsubscribe()
        }
        setPushEnabled(false)
      } else {
        const { key: vapidKey } = await api.getVapidPublicKey()
        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: vapidKey,
        })
        const keys = sub.toJSON().keys
        const id = btoa(sub.endpoint).slice(0, 32)
        await api.subscribePush({ id, endpoint: sub.endpoint, p256dh: keys.p256dh, auth: keys.auth })
        setPushEnabled(true)
      }
    } catch (e) {
      console.error('Push toggle failed:', e)
    }
    setPushLoading(false)
  }, [pushEnabled])

  const starMutation = useMutation({
    mutationFn: (id) => api.toggleStarred(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['starred'] }),
  })

  const [alertsOpen, setAlertsOpen] = useState(null)
  const [alertForm, setAlertForm] = useState({ desktop: true, zapier_webhook: '', notify_coming_soon_only: false, alerts_paused: false, recipients: [] })
  const [recipientInput, setRecipientInput] = useState('')

  const [showSearches, setShowSearches] = useState(true)
  const [showDismissed, setShowDismissed] = useState(false)
  useEffect(() => {
    const handleScroll = () => { if (window.scrollY > 120) setShowSearches(false) }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const notifMutation = useMutation({
    mutationFn: ({ id, settings }) => api.updateNotifications(id, settings),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['searches'] }); setAlertsOpen(null) },
  })
  const runMutation = useMutation({
    mutationFn: (id) => api.runSearch(id),
    onSuccess: (data, id) => { queryClient.invalidateQueries({ queryKey: ['searches'] }); navigate(`/search/${id}/results`) },
  })
  const deleteMutation = useMutation({
    mutationFn: (id) => api.deleteSearch(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['searches'] }),
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, criteria, name }) => api.updateSearch(id, criteria, name),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['searches'] })
      setEditingSearch(null)
      runMutation.mutate(id)
    },
  })
  const [editingSearch, setEditingSearch] = useState(null)

  const { settings: mortgageSettings } = useMortgage()
  const { data: settingsData } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings, staleTime: 300000 })
  const workLocation = (settingsData?.work_lat && settingsData?.work_lng)
    ? { lat: settingsData.work_lat, lng: settingsData.work_lng }
    : null
  return (
    <div>
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={32} className="animate-spin text-amber-500" />
        </div>
      ) : searches.length === 0 ? (
        /* Hero empty state — full viewport */
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] text-center px-4">
          <h2 className="font-serif text-4xl sm:text-5xl text-ink-primary mb-3">Search smarter.</h2>
          <p className="text-ink-secondary text-base sm:text-lg mb-6">Find faster. No ads. No dark patterns.</p>
          <Button onClick={() => navigate('/search/new')} size="lg">
            Start Your First Search →
          </Button>

          {/* Session card for fresh devices */}
          <div className="mt-10 w-full max-w-sm bg-canvas-900 border border-canvas-700 rounded-xl p-5">
            {/* This device's session — scan to share */}
            {sessionCode && (
              <div className="mb-5">
                <p className="text-xs text-ink-muted text-center mb-3">Your session — scan from another device to share your searches &amp; dismissals</p>
                <div className="flex flex-col items-center gap-2">
                  <div className="p-3 bg-white rounded-xl">
                    <QRCodeSVG value={`${appUrl}?s=${sessionCode}`} size={160} />
                  </div>
                  <p className="text-lg font-mono tracking-[0.3em] text-amber-400 font-bold">{sessionCode}</p>
                </div>
              </div>
            )}

            {/* Divider */}
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-1 h-px bg-canvas-700" />
              <span className="text-xs text-ink-muted">or join an existing session</span>
              <div className="flex-1 h-px bg-canvas-700" />
            </div>

            {/* Join another session */}
            <div className="flex gap-2">
              <input
                value={manualCode}
                onChange={(e) => { setManualCode(e.target.value.toUpperCase().slice(0, 6)); setSessionError('') }}
                onKeyDown={(e) => e.key === 'Enter' && applySessionCode(manualCode)}
                placeholder="XXXXXX"
                maxLength={6}
                className="flex-1 px-3 py-2 text-base font-mono tracking-widest text-center bg-canvas-800 border border-canvas-600 rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:border-amber-500 uppercase"
              />
              <button
                onClick={() => applySessionCode(manualCode)}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30 transition-colors"
              >
                Join
              </button>
            </div>
            {sessionError && <p className="text-xs text-red-400 mt-1 text-center">{sessionError}</p>}
          </div>
        </div>
      ) : (
        <>
        {/* Stats — compact inline strip */}
        <div className="flex items-center gap-2 mb-6 text-sm flex-wrap">
          <span className="font-mono text-amber-400 font-semibold">{totalSearches}</span>
          <span className="text-ink-muted">searches</span>
          <span className="text-canvas-600 mx-1">·</span>
          <span className="font-mono text-amber-400 font-semibold">{totalProperties.toLocaleString()}</span>
          <span className="text-ink-muted">properties</span>
          <span className="text-canvas-600 mx-1">·</span>
          <span className="font-mono text-amber-400 font-semibold">{activeSearches}</span>
          <span className="text-ink-muted">active</span>
        </div>

        {/* New Listings — prominent section shown only when new finds exist */}
        {(() => {
          const newListings = allListings.filter(l => l.is_new)
          if (newListings.length === 0) return null
          return (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
                  </span>
                  <h2 className="font-sans text-lg font-semibold text-ink-primary">New Listings</h2>
                  <span className="px-2 py-0.5 text-xs font-bold bg-green-500/20 text-green-400 border border-green-500/40 rounded-full">{newListings.length}</span>
                </div>
                <button
                  onClick={() => navigate('/search/all?filter=new')}
                  className="text-xs text-amber-400 hover:text-amber-300 transition-colors"
                >
                  View all →
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {newListings.slice(0, 8).map((listing, i) => (
                  <PropertyCard
                    key={`${listing.source}-${listing.source_id}-${i}`}
                    listing={listing}
                    onDismiss={handleDismiss}
                    onToggleStar={listing.id ? () => starMutation.mutate(listing.id) : undefined}
                    mortgageSettings={mortgageSettings.enabled ? mortgageSettings : null}
                    workLocation={workLocation}
                  />
                ))}
              </div>
            </div>
          )
        })()}

        {/* Push Notifications toggle */}
        {'serviceWorker' in navigator && 'PushManager' in window && (
          <div className="flex items-center justify-between bg-canvas-900 border border-canvas-700 rounded-xl px-4 py-3 mb-6">
            <div className="flex items-center gap-3">
              {pushEnabled ? <Bell size={16} className="text-amber-400" /> : <BellOff size={16} className="text-ink-muted" />}
              <div>
                <p className="text-sm font-medium text-ink-primary">Phone &amp; Browser Notifications</p>
                <p className="text-xs text-ink-muted">{pushEnabled ? 'You\'ll get a lock-screen alert when new listings are found.' : 'Get alerts on this device when new listings are found.'}</p>
              </div>
            </div>
            <button
              onClick={togglePush}
              disabled={pushLoading}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${pushEnabled ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/40' : 'bg-canvas-800 text-ink-secondary border border-canvas-600 hover:border-amber-500 hover:text-amber-400'}`}
            >
              {pushLoading ? <Loader2 size={12} className="animate-spin" /> : pushEnabled ? 'Disable' : 'Enable'}
            </button>
          </div>
        )}

        {/* Connect another device via QR */}
        <div className="bg-canvas-900 border border-canvas-700 rounded-xl px-4 py-3 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <QrCode size={16} className="text-ink-muted" />
              <div>
                <p className="text-sm font-medium text-ink-primary">Connect Another Device</p>
                <p className="text-xs text-ink-muted font-mono">
                  {appUrl}
                  {sessionCode && <span className="text-amber-400/80"> · Session {sessionCode}</span>}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowQr(v => !v)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-canvas-800 text-ink-secondary border border-canvas-600 hover:border-amber-500 hover:text-amber-400 transition-colors"
            >
              {showQr ? 'Hide' : 'Show QR'}
            </button>
          </div>
          {showQr && (
            <div className="mt-4 flex flex-col items-center gap-3">
              <div className="p-3 bg-white rounded-xl">
                <QRCodeSVG value={sessionCode ? `${appUrl}?s=${sessionCode}` : appUrl} size={180} />
              </div>
              <p className="text-sm font-mono tracking-[0.3em] text-amber-400 font-bold">{sessionCode}</p>
              <p className="text-xs text-ink-muted text-center max-w-xs">Scan QR or enter the code above on another device — dismissed houses and saved searches transfer instantly.</p>

              {/* Manual code entry */}
              <div className="w-full max-w-xs mt-1">
                <p className="text-xs text-ink-muted mb-1.5 text-center">Or enter someone else's session code:</p>
                <div className="flex gap-2">
                  <input
                    value={manualCode}
                    onChange={(e) => { setManualCode(e.target.value.toUpperCase().slice(0, 6)); setSessionError('') }}
                    onKeyDown={(e) => e.key === 'Enter' && applySessionCode(manualCode)}
                    placeholder="XXXXXX"
                    maxLength={6}
                    className="flex-1 px-3 py-1.5 text-sm font-mono tracking-widest text-center bg-canvas-800 border border-canvas-600 rounded-lg text-ink-primary placeholder:text-ink-muted focus:outline-none focus:border-amber-500 uppercase"
                  />
                  <button
                    onClick={() => applySessionCode(manualCode)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30 transition-colors"
                  >
                    Join
                  </button>
                </div>
                {sessionError && <p className="text-xs text-red-400 mt-1 text-center">{sessionError}</p>}
              </div>
            </div>
          )}
        </div>

        {/* Saved Searches */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-sans text-lg font-semibold text-ink-primary">Saved Searches</h2>
          <button
            onClick={() => setShowSearches(v => !v)}
            className="flex items-center gap-1.5 text-xs text-ink-muted hover:text-amber-400 transition-colors px-2 py-1 rounded-lg border border-canvas-700 hover:border-amber-500/50"
          >
            {showSearches ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            {showSearches ? 'Hide' : `Show (${searches.length})`}
          </button>
        </div>
        {showSearches && <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {searches.map((s) => {
            const c = s.criteria
            const priceRange = (c.price_min || c.price_max)
              ? `$${(c.price_min || 0).toLocaleString()} – $${c.price_max ? c.price_max.toLocaleString() : '∞'}`
              : 'Any price'

            return (
              <div
                key={s.id}
                className="bg-canvas-900 border border-canvas-700 rounded-xl p-5 hover:border-canvas-500 hover:shadow-card-hover transition-all duration-200"
              >
                {/* Card header */}
                <div className="flex justify-between items-start mb-3">
                  <h3 className="font-semibold text-ink-primary text-base leading-tight pr-2">{s.name}</h3>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {s.new_count > 0 && (
                      <span className="text-xs rounded-full px-2.5 py-0.5 font-medium bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse">
                        {s.new_count} new
                      </span>
                    )}
                    <span className={`text-xs rounded-full px-2.5 py-0.5 font-medium ${
                      s.is_active
                        ? 'bg-match-strong/10 text-match-strong border border-match-strong/30'
                        : 'bg-canvas-700 text-ink-muted'
                    }`}>
                      {s.is_active ? '● Active' : 'Paused'}
                    </span>
                  </div>
                </div>

                {/* Criteria summary */}
                <div className="space-y-1 text-sm text-ink-secondary mb-3">
                  <p className="flex items-center gap-1.5 text-xs">
                    <MapPin size={12} className="text-ink-muted" />
                    {c.location || 'No location'}
                    {c.radius_miles && <span className="text-ink-muted">· {c.radius_miles}mi</span>}
                  </p>
                  <p className="flex items-center gap-1.5 text-xs">
                    <DollarSign size={12} className="text-ink-muted" /> {priceRange}
                  </p>
                  {(c.bedrooms_min || c.bathrooms_min || c.sqft_min) && (
                    <p className="text-xs text-ink-muted">
                      {c.bedrooms_min && `${c.bedrooms_min}+ bd`}
                      {c.bathrooms_min && ` · ${c.bathrooms_min}+ ba`}
                      {c.sqft_min && ` · ${c.sqft_min.toLocaleString()}+ sqft`}
                    </p>
                  )}
                  <p className="flex items-center gap-1.5 text-xs text-ink-muted">
                    <Clock size={11} />
                    {s.last_run_at ? `Last run: ${new Date(s.last_run_at).toLocaleString()}` : 'Never run'}
                  </p>
                  {s.result_count != null && (
                    <p className="text-xs font-mono text-amber-500">{s.result_count.toLocaleString()} properties</p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    className="flex-1"
                    onClick={() => runMutation.mutate(s.id)}
                    disabled={runMutation.isPending}
                  >
                    {runMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                    Run Now
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => navigate(`/search/${s.id}/results`)}>
                    Results
                  </Button>
                  <button
                    title="Edit search criteria"
                    onClick={() => setEditingSearch(s)}
                    className="p-2 rounded-lg border border-canvas-600 text-ink-muted hover:border-amber-500 hover:text-amber-400 transition-colors"
                  >
                    <Pencil size={14} />
                  </button>
                  {/* Bell = alerts on/off toggle */}
                  <button
                    title={s.notification_settings?.alerts_paused ? 'Alerts off — click to turn on' : 'Alerts on — click to turn off'}
                    onClick={() => notifMutation.mutate({
                      id: s.id,
                      settings: { ...(s.notification_settings || {}), alerts_paused: !s.notification_settings?.alerts_paused }
                    })}
                    className={`p-2 rounded-lg border transition-colors ${!s.notification_settings?.alerts_paused ? 'border-amber-500/50 text-amber-400' : 'border-canvas-600 text-ink-muted hover:border-canvas-500'}`}
                  >
                    {s.notification_settings?.alerts_paused ? <BellOff size={15} /> : <Bell size={15} />}
                  </button>
                  {/* Settings gear — per-search options */}
                  <button
                    onClick={() => {
                      if (alertsOpen === s.id) {
                        setAlertsOpen(null)
                      } else {
                        setAlertForm({
                          desktop: s.notification_settings?.desktop ?? true,
                          zapier_webhook: s.notification_settings?.zapier_webhook ?? '',
                          notify_coming_soon_only: s.notification_settings?.notify_coming_soon_only ?? false,
                          alerts_paused: s.notification_settings?.alerts_paused ?? false,
                          recipients: s.notification_settings?.recipients ?? [],
                        })
                        setRecipientInput('')
                        setAlertsOpen(s.id)
                      }
                    }}
                    className="p-2 rounded-lg border border-canvas-600 hover:border-canvas-500 transition-colors"
                  >
                    <Settings2 size={15} className="text-ink-muted" />
                  </button>
                  <button
                    onClick={() => { if (confirm(`Delete "${s.name}"?`)) deleteMutation.mutate(s.id) }}
                    className="p-2 rounded-lg border border-canvas-600 hover:border-red-500/50 transition-colors"
                  >
                    <Trash2 size={15} className="text-red-500/70" />
                  </button>
                </div>

                {/* Alert settings panel */}
                {alertsOpen === s.id && (
                  <div className="mt-4 pt-4 border-t border-canvas-700 space-y-3">
                    <p className="text-sm font-medium text-ink-primary">Alert Settings</p>
                    <label className="flex items-center gap-2 text-sm text-ink-secondary cursor-pointer">
                      <input
                        type="checkbox"
                        checked={alertForm.desktop}
                        onChange={(e) => setAlertForm(f => ({ ...f, desktop: e.target.checked }))}
                        className="rounded border-canvas-600 bg-canvas-800 accent-amber-500"
                      />
                      Desktop notifications
                    </label>
                    <p className="text-xs text-ink-muted">Webhook URL is set globally in <span className="text-amber-400">Settings</span>.</p>
                    <label className="flex items-center gap-2 text-sm text-ink-secondary cursor-pointer">
                      <input
                        type="checkbox"
                        checked={alertForm.notify_coming_soon_only}
                        onChange={(e) => setAlertForm(f => ({ ...f, notify_coming_soon_only: e.target.checked }))}
                        className="rounded border-canvas-600 bg-canvas-800 accent-amber-500"
                      />
                      Coming Soon listings only
                    </label>

                    {/* Recipients */}
                    <div>
                      <label className="block text-xs text-ink-muted mb-1">Recipients (phone numbers)</label>
                      <div className="flex gap-2 mb-2">
                        <input
                          type="tel"
                          value={recipientInput}
                          onChange={(e) => setRecipientInput(e.target.value)}
                          onKeyDown={(e) => {
                            if ((e.key === 'Enter' || e.key === ',') && recipientInput.trim()) {
                              e.preventDefault()
                              const num = recipientInput.trim().replace(/,/g, '')
                              if (num && !alertForm.recipients.includes(num)) {
                                setAlertForm(f => ({ ...f, recipients: [...f.recipients, num] }))
                              }
                              setRecipientInput('')
                            }
                          }}
                          placeholder="+15165551234"
                          className="flex-1 px-3 py-1.5 text-sm bg-canvas-800 border border-canvas-600 rounded-lg text-ink-secondary placeholder:text-ink-muted focus:outline-none focus:border-amber-500"
                        />
                        <button
                          onClick={() => {
                            const num = recipientInput.trim()
                            if (num && !alertForm.recipients.includes(num)) {
                              setAlertForm(f => ({ ...f, recipients: [...f.recipients, num] }))
                            }
                            setRecipientInput('')
                          }}
                          className="px-2 py-1.5 rounded-lg border border-canvas-600 hover:border-amber-500 text-ink-muted hover:text-amber-400 transition-colors"
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                      {alertForm.recipients.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {alertForm.recipients.map(r => (
                            <span key={r} className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-canvas-800 border border-canvas-600 text-ink-secondary">
                              {r}
                              <button onClick={() => setAlertForm(f => ({ ...f, recipients: f.recipients.filter(x => x !== r) }))} className="text-ink-muted hover:text-red-400">
                                <X size={10} />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                      <p className="text-xs text-ink-muted mt-1">Included as <code className="text-amber-400/80">recipients</code> array in the Zapier payload — loop over them in your Zap to send to multiple numbers.</p>
                    </div>

                    <Button
                      variant="default"
                      size="sm"
                      className="w-full"
                      onClick={() => notifMutation.mutate({ id: s.id, settings: alertForm })}
                      disabled={notifMutation.isPending}
                    >
                      {notifMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                      Save Alert Settings
                    </Button>
                  </div>
                )}
              </div>
            )
          })}
        </div>}

        {/* Recent Activity */}
        {recentSearch && recentResults.length > 0 && (
          <div className="mt-10">
            <h2 className="font-sans text-lg font-semibold text-ink-primary mb-4">
              Recent — <span className="text-ink-muted font-normal">{recentSearch.name}</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {recentResults.map((listing, i) => (
                <PropertyCard
                  key={`${listing.source}-${listing.source_id}-${i}`}
                  listing={listing}
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

        {/* Saved Listings */}
        {filteredStarred.length > 0 && (
          <div className="mt-10">
            <div className="flex items-center gap-3 mb-4">
              <h2 className="font-sans text-lg font-semibold text-ink-primary flex items-center gap-2">
                <Bookmark size={18} className="text-amber-400 fill-current" />
                Saved Listings
              </h2>
              <span className="font-mono text-xs text-ink-muted bg-canvas-800 border border-canvas-600 px-2 py-0.5 rounded-full">
                {filteredStarred.length}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredStarred.map((listing, i) => (
                <PropertyCard
                  key={`${listing.source}-${listing.source_id}-${i}`}
                  listing={listing}
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

        {/* All Listings — merged, deduplicated, dismissed filtered */}
        {/* Wait for dismissedQuery before rendering so dismissed listings never flash visible */}
        {allListingsQuery.isSuccess && dismissedQuery.isSuccess && unsectionedListings.length > 0 && (
          <div className="mt-10">
            <div className="flex items-center gap-3 mb-4 flex-wrap">
              <h2 className="font-sans text-lg font-semibold text-ink-primary flex items-center gap-2">
                <Home size={18} className="text-amber-400" />
                All Listings
              </h2>
              <span className="font-mono text-xs text-ink-muted bg-canvas-800 border border-canvas-600 px-2 py-0.5 rounded-full">
                {unsectionedListings.length}
              </span>
              {dismissedIds.size > 0 && (
                <button
                  onClick={() => setShowDismissed(v => !v)}
                  className="text-xs text-ink-muted hover:text-ink-secondary border border-canvas-600 hover:border-canvas-500 px-2 py-0.5 rounded-full transition-colors"
                >
                  {showDismissed ? 'Hide dismissed' : `Show dismissed (${dismissedIds.size})`}
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {unsectionedListings.map((listing, i) => (
                <PropertyCard
                  key={`${listing.source}-${listing.source_id}-${i}`}
                  listing={listing}
                  onToggleStar={starMutation.mutate}
                  mortgageSettings={mortgageSettings.enabled ? mortgageSettings : null}
                  onDismiss={handleDismiss}
                  commuteMinutes={workLocation && listing.latitude && listing.longitude
                    ? estimateCommute(listing.latitude, listing.longitude, workLocation.lat, workLocation.lng)
                    : null}
                />
              ))}
            </div>

            {/* Dismissed listings — compact undo list */}
            {showDismissed && dismissedListings.length > 0 && (
              <div className="mt-6">
                <p className="text-xs text-ink-muted mb-3">Hidden from all results — click Undo to restore.</p>
                <div className="space-y-2">
                  {dismissedListings.map((listing) => (
                    <div
                      key={listing.source_id}
                      className="flex items-center justify-between bg-canvas-900 border border-canvas-700 rounded-lg px-4 py-3 opacity-50"
                    >
                      <div className="min-w-0">
                        <p className="text-sm text-ink-secondary line-clamp-1">{listing.address || 'Unknown address'}</p>
                        <p className="text-xs text-ink-muted">
                          {listing.price ? `$${listing.price.toLocaleString()}` : ''}
                          {listing.city ? ` · ${listing.city}${listing.state ? `, ${listing.state}` : ''}` : ''}
                        </p>
                      </div>
                      <button
                        onClick={() => undismissMutation.mutate(listing.source_id)}
                        disabled={undismissMutation.isPending}
                        className="ml-3 shrink-0 px-3 py-1 text-xs rounded-lg border border-canvas-600 text-ink-muted hover:border-amber-500 hover:text-amber-400 transition-colors disabled:opacity-50"
                      >
                        Undo
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </>
      )}

      {/* Edit search modal */}
      {editingSearch && (
        <div className="fixed inset-0 z-[9999] flex flex-col bg-canvas-950/95 backdrop-blur-sm">
          <div className="flex items-center justify-between px-4 py-3 border-b border-canvas-700 bg-canvas-900 shrink-0">
            <p className="text-sm font-semibold text-ink-primary">Edit: {editingSearch.name}</p>
            <button onClick={() => setEditingSearch(null)} className="p-2 rounded-lg hover:bg-canvas-800 text-ink-muted hover:text-ink-primary transition-colors">
              <X size={18} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <SearchForm
              initialCriteria={editingSearch.criteria}
              searchName={editingSearch.name}
              onSearch={(criteria, name) => {
                updateMutation.mutate({ id: editingSearch.id, criteria, name: name || editingSearch.name })
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
