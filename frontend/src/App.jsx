import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Home, Moon, Sun, Circle, Mail, Loader2, AlertTriangle, Map } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import NewSearch from './pages/NewSearch'
import SearchResults from './pages/SearchResults'
import Settings from './pages/Settings'
import MapView from './pages/MapView'
import MortgageCalculator from './pages/MortgageCalculator'
import { api } from './api'
import MortgageBar, { MortgageProvider } from './components/MortgageBar'

function Nav() {
  const location = useLocation()
  const isActive = (path) => location.pathname === path
  const reportMutation = useMutation({ mutationFn: () => api.sendReport() })
  const { data: settingsStatus } = useQuery({ queryKey: ['settings-status'], queryFn: api.getSettingsStatus, staleTime: 60000 })
  const { data: versionData } = useQuery({ queryKey: ['version'], queryFn: api.getVersion, staleTime: Infinity })
  const smtpConfigured = settingsStatus?.smtp_configured ?? null

  const [theme, setTheme] = useState(() => localStorage.getItem('hf_theme') || 'light')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const applyTheme = (t) => { localStorage.setItem('hf_theme', t); setTheme(t) }

  return (
    <nav className="bg-canvas-850 border-b border-canvas-700 h-14 sm:h-16 sticky top-0 z-30">
      <div className="max-w-screen-2xl mx-auto px-3 sm:px-6 h-full flex items-center gap-2 sm:gap-6">
        <Link to="/" className="flex items-center gap-2 shrink-0 min-w-0">
          <Home size={20} className="text-amber-400 shrink-0" />
          <div className="flex flex-col leading-tight min-w-0">
            <span className="font-serif text-lg sm:text-xl text-ink-primary whitespace-nowrap">HomerFindr</span>
            <span className="hidden sm:flex items-center gap-1.5 text-[10px] text-ink-muted italic">
              Can't believe I missed another listing! Doh!
              {versionData?.version && (
                <span className="not-italic text-[9px] font-mono bg-canvas-700 text-ink-muted px-1 py-0.5 rounded">v{versionData.version}</span>
              )}
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-0 sm:gap-1 min-w-0 overflow-x-auto">
          <Link to="/" className={`px-1.5 sm:px-4 py-1.5 text-xs sm:text-sm rounded-md transition-colors whitespace-nowrap ${isActive('/') ? 'text-amber-400 font-medium' : 'text-ink-secondary hover:text-ink-primary'}`}>
            <span className="sm:hidden">Home</span>
            <span className="hidden sm:inline">Dashboard</span>
          </Link>
          <Link to="/search/new" className={`px-1.5 sm:px-4 py-1.5 text-xs sm:text-sm rounded-md transition-colors whitespace-nowrap ${isActive('/search/new') ? 'text-amber-400 font-medium' : 'text-ink-secondary hover:text-ink-primary'}`}>
            <span className="sm:hidden">Search</span>
            <span className="hidden sm:inline">New Search</span>
          </Link>
          <Link to="/map" className={`flex items-center gap-1 px-1.5 sm:px-4 py-1.5 text-xs sm:text-sm rounded-md transition-colors whitespace-nowrap ${isActive('/map') ? 'text-amber-400 font-medium' : 'text-ink-secondary hover:text-ink-primary'}`}>
            <Map size={14} />
            Map
          </Link>
          <Link to="/mortgage" className={`flex items-center gap-1 px-1.5 sm:px-4 py-1.5 text-xs sm:text-sm rounded-md transition-colors whitespace-nowrap ${isActive('/mortgage') ? 'text-amber-400 font-medium' : 'text-ink-secondary hover:text-ink-primary'}`}>
            <span className="sm:hidden">Calc</span>
            <span className="hidden sm:inline">Mortgage</span>
          </Link>
          <Link to="/settings" className={`px-1.5 sm:px-4 py-1.5 text-xs sm:text-sm rounded-md transition-colors whitespace-nowrap ${isActive('/settings') ? 'text-amber-400 font-medium' : 'text-ink-secondary hover:text-ink-primary'}`}>
            Settings
          </Link>
        </div>

        <div className="ml-auto flex items-center gap-1 sm:gap-3 shrink-0">
          {/* Email button — icon only on mobile */}
          {smtpConfigured === false ? (
            <Link
              to="/settings"
              title="Setup Email"
              className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-md border border-amber-500/50 text-amber-400 hover:border-amber-500 hover:bg-amber-500/10 transition-colors"
            >
              <AlertTriangle size={14} />
              <span>Email</span>
            </Link>
          ) : smtpConfigured === true ? (
            <button
              onClick={() => reportMutation.mutate()}
              disabled={reportMutation.isPending}
              title="Send Report"
              className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-md border border-canvas-600 text-ink-secondary hover:text-amber-400 hover:border-amber-500 transition-colors disabled:opacity-50"
            >
              {reportMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
              <span className="hidden sm:inline">Send Report</span>
            </button>
          ) : null}

          <div className="hidden sm:flex items-center gap-1">
            <button onClick={() => applyTheme('dark')} title="Dark" className={`p-2 rounded-md transition-colors ${theme === 'dark' ? 'text-amber-400' : 'text-ink-secondary hover:text-ink-primary'}`}><Moon size={16} /></button>
            <button onClick={() => applyTheme('light')} title="Light" className={`p-2 rounded-md transition-colors ${theme === 'light' ? 'text-amber-400' : 'text-ink-secondary hover:text-ink-primary'}`}><Sun size={16} /></button>
            <button onClick={() => applyTheme('grey')} title="Grey" className={`p-2 rounded-md transition-colors ${theme === 'grey' ? 'text-amber-400' : 'text-ink-secondary hover:text-ink-primary'}`}><Circle size={16} /></button>
          </div>
        </div>
      </div>

      {reportMutation.isSuccess && (
        <div className="fixed bottom-4 right-4 bg-canvas-800 border border-canvas-600 text-ink-primary px-4 py-2 rounded-xl shadow-card-hover z-50">
          Report sent ✓
        </div>
      )}
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <MortgageProvider>
        <div className="min-h-screen bg-canvas-950">
          <Nav />
          <MortgageBar />
          <main className="max-w-screen-2xl mx-auto px-6 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/search/new" element={<NewSearch />} />
              <Route path="/search/:id/results" element={<SearchResults />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/map" element={<MapView />} />
              <Route path="/mortgage" element={<MortgageCalculator />} />
            </Routes>
          </main>
        </div>
      </MortgageProvider>
    </BrowserRouter>
  )
}
