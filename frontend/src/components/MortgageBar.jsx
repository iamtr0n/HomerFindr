import { createContext, useContext, useState, useEffect } from 'react'
import { Calculator } from 'lucide-react'

const STORAGE_KEY = 'hf_mortgage'

const defaults = { rate: 7.0, downPct: 20, termYears: 30, enabled: false, budgetMax: null }

function load() {
  try { return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') } }
  catch { return defaults }
}

export const MortgageContext = createContext(null)

export function useMortgage() {
  return useContext(MortgageContext)
}

export function MortgageProvider({ children }) {
  const [settings, setSettings] = useState(load)

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)) } catch {}
  }, [settings])

  return (
    <MortgageContext.Provider value={{ settings, setSettings }}>
      {children}
    </MortgageContext.Provider>
  )
}

export default function MortgageBar() {
  const { settings, setSettings } = useMortgage()
  const set = (key) => (e) => setSettings(s => ({ ...s, [key]: e.target.value === '' ? null : parseFloat(e.target.value) }))

  return (
    <div className="border-b border-canvas-700 bg-canvas-900">
      <div className="max-w-screen-2xl mx-auto px-6 py-2 flex items-center gap-4 flex-wrap">
        <button
          onClick={() => setSettings(s => ({ ...s, enabled: !s.enabled }))}
          className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${
            settings.enabled ? 'text-amber-400' : 'text-ink-muted hover:text-ink-secondary'
          }`}
        >
          <Calculator size={13} />
          Mortgage
          <div className={`w-7 h-3.5 rounded-full transition-colors relative ml-0.5 ${settings.enabled ? 'bg-amber-500' : 'bg-canvas-600'}`}>
            <div className={`absolute top-0.5 w-2.5 h-2.5 bg-white rounded-full shadow transition-transform ${settings.enabled ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
          </div>
        </button>

        {settings.enabled && (
          <>
            <div className="flex items-center gap-1.5 text-xs text-ink-muted">
              <span>Rate</span>
              <input
                type="number" step="0.1" min="1" max="20"
                value={settings.rate ?? ''}
                onChange={set('rate')}
                className="w-14 py-0.5 px-1.5 bg-canvas-800 border border-canvas-600 rounded text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
              />
              <span>%</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-ink-muted">
              <span>Down</span>
              <input
                type="number" step="1" min="0" max="100"
                value={settings.downPct ?? ''}
                onChange={set('downPct')}
                className="w-12 py-0.5 px-1.5 bg-canvas-800 border border-canvas-600 rounded text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
              />
              <span>%</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-ink-muted">
              <span>Term</span>
              <select
                value={settings.termYears}
                onChange={(e) => setSettings(s => ({ ...s, termYears: +e.target.value }))}
                className="py-0.5 px-1.5 bg-canvas-800 border border-canvas-600 rounded text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
              >
                <option value={10}>10 yr</option>
                <option value={15}>15 yr</option>
                <option value={20}>20 yr</option>
                <option value={30}>30 yr</option>
              </select>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-ink-muted">
              <span>Budget</span>
              <span className="text-ink-muted">$</span>
              <input
                type="number" step="50" min="0"
                placeholder="target/mo"
                value={settings.budgetMax || ''}
                onChange={(e) => setSettings(s => ({ ...s, budgetMax: e.target.value ? parseFloat(e.target.value) : null }))}
                className="w-24 py-0.5 px-1.5 bg-canvas-800 border border-canvas-600 rounded text-xs text-ink-secondary focus:border-amber-500 focus:outline-none"
              />
              <span>/mo</span>
            </div>
            <span className="text-xs text-ink-muted">· Est. monthly shown on each card</span>
          </>
        )}
      </div>
    </div>
  )
}
