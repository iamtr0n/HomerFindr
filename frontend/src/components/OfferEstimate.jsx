import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, Sparkles, Calculator, AlertTriangle, Flame, Snowflake, Scale, Camera } from 'lucide-react'

function fmt(n) {
  if (!n && n !== 0) return '—'
  return '$' + Math.round(n).toLocaleString()
}

function fmtPct(n) {
  if (!n && n !== 0) return ''
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

function MarketBadge({ condition, overbidRatio, avgDom }) {
  if (!condition) return null
  const config = {
    hot:      { cls: 'bg-red-500/15 text-red-400 border-red-500/30',    Icon: Flame,     label: 'Hot market' },
    balanced: { cls: 'bg-sky-500/15 text-sky-400 border-sky-500/30',    Icon: Scale,     label: 'Balanced market' },
    cool:     { cls: 'bg-blue-500/15 text-blue-400 border-blue-500/30', Icon: Snowflake, label: 'Cool market' },
  }
  const { cls, Icon, label } = config[condition] || config.balanced
  const ratioStr = overbidRatio ? ` · ${overbidRatio > 1 ? '+' : ''}${((overbidRatio - 1) * 100).toFixed(1)}% sold/list` : ''
  const domStr = avgDom ? ` · ${Math.round(avgDom)}d avg DOM` : ''
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cls}`}>
      <Icon size={11} />
      {label}{ratioStr}{domStr}
    </span>
  )
}

function AssessmentBadge({ assessment, pct }) {
  if (!assessment) return null
  const config = {
    underpriced:  { cls: 'bg-green-500/15 text-green-400 border-green-500/30', Icon: TrendingDown, label: 'Potentially underpriced' },
    fairly_priced:{ cls: 'bg-sky-500/15 text-sky-400 border-sky-500/30',       Icon: Minus,        label: 'Fairly priced' },
    overpriced:   { cls: 'bg-red-500/15 text-red-400 border-red-500/30',       Icon: TrendingUp,   label: 'Potentially overpriced' },
  }
  const { cls, Icon, label } = config[assessment] || config.fairly_priced
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cls}`}>
      <Icon size={12} />
      {label} ({fmtPct(pct)} vs estimate)
    </span>
  )
}

function ConfidencePip({ level }) {
  const colors = { high: 'bg-green-400', medium: 'bg-amber-400', low: 'bg-red-400' }
  return <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${colors[level] || 'bg-canvas-500'}`} />
}

function OfferTierRow({ label, amount, highlight }) {
  return (
    <div className={`flex justify-between items-center py-1.5 px-3 rounded-lg ${highlight ? 'bg-match-strong/10 border border-match-strong/20' : ''}`}>
      <span className={`text-sm ${highlight ? 'text-match-strong font-semibold' : 'text-ink-muted'}`}>{label}</span>
      <span className={`text-sm font-mono font-semibold ${highlight ? 'text-match-strong' : 'text-ink-base'}`}>{fmt(amount)}</span>
    </div>
  )
}

function LogicalSection({ logical, listingPrice }) {
  const [showAdj, setShowAdj] = useState(false)
  const [showComps, setShowComps] = useState(false)
  if (!logical) return null
  const hasAdj = Object.keys(logical.adjustments || {}).length > 0

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Calculator size={14} className="text-match-good" />
          <span className="text-sm font-semibold text-ink-base">CMA Estimate</span>
          <span className="text-xs text-ink-muted">({logical.comp_count} comps, recency-weighted)</span>
        </div>
        <div className="flex items-center text-xs text-ink-muted">
          <ConfidencePip level={logical.confidence} />
          {logical.confidence} confidence
        </div>
      </div>

      {/* Market condition */}
      <MarketBadge
        condition={logical.market_condition}
        overbidRatio={logical.market_overbid_ratio}
        avgDom={logical.avg_days_on_market}
      />

      <div className="flex items-center justify-between text-xs text-ink-muted px-1">
        <span>Weighted median {fmt(logical.price_per_sqft_comps)}/sqft × sqft</span>
        <span className="font-mono text-ink-base font-medium">Est. {fmt(logical.estimated_value)}</span>
      </div>

      {hasAdj && (
        <button onClick={() => setShowAdj(v => !v)} className="flex items-center gap-1 text-xs text-ink-muted hover:text-ink-base transition-colors px-1">
          {showAdj ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          Feature adjustments applied
        </button>
      )}
      {showAdj && hasAdj && (
        <div className="bg-canvas-800 rounded-lg px-3 py-2 space-y-1">
          {Object.entries(logical.adjustments).map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs">
              <span className="text-ink-muted capitalize">{k.replace(/_/g, ' ')}</span>
              <span className={`font-mono ${v >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {v >= 0 ? '+' : ''}{fmt(v)}
              </span>
            </div>
          ))}
        </div>
      )}

      <AssessmentBadge assessment={logical.value_assessment} pct={logical.price_vs_estimate_pct} />

      <div className="space-y-1">
        <OfferTierRow label={logical.market_condition === 'hot' ? 'At list (minimum)' : 'Conservative offer'} amount={logical.offer_low} />
        <OfferTierRow label="Fair offer" amount={logical.offer_fair} highlight />
        <OfferTierRow label={logical.market_condition === 'hot' ? 'Strong (above list)' : 'Strong offer'} amount={logical.offer_strong} />
      </div>
    </div>
  )
}

function AISection({ ai }) {
  if (!ai) return null

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-purple-400" />
          <span className="text-sm font-semibold text-ink-base">AI Analysis</span>
          <span className="text-xs text-ink-muted">(Claude Sonnet)</span>
        </div>
        <div className="flex items-center text-xs text-ink-muted">
          <ConfidencePip level={ai.confidence} />
          {ai.confidence} confidence
        </div>
      </div>

      <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-ink-muted">Suggested offer</span>
          <span className="text-lg font-bold font-mono text-purple-300">{fmt(ai.suggested_offer)}</span>
        </div>
        <div className="flex items-center justify-between text-xs text-ink-muted">
          <span>Range</span>
          <span className="font-mono">{fmt(ai.offer_range_low)} — {fmt(ai.offer_range_high)}</span>
        </div>
      </div>

      {/* Photo/condition assessment */}
      {ai.condition_assessment && ai.condition_assessment !== 'Photo not available' && (
        <div className="flex gap-2 text-xs bg-canvas-800 rounded-lg px-3 py-2">
          <Camera size={12} className="text-ink-muted shrink-0 mt-0.5" />
          <p className="text-ink-muted leading-relaxed">{ai.condition_assessment}</p>
        </div>
      )}

      {ai.market_assessment && (
        <p className="text-xs text-ink-muted leading-relaxed italic">"{ai.market_assessment}"</p>
      )}

      {ai.reasoning && (
        <p className="text-xs text-ink-base leading-relaxed">{ai.reasoning}</p>
      )}

      {ai.negotiation_tips?.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-ink-base">Negotiation tips</p>
          <ul className="space-y-1">
            {ai.negotiation_tips.map((tip, i) => (
              <li key={i} className="text-xs text-ink-muted flex gap-2">
                <span className="text-match-good mt-0.5">›</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {ai.red_flags?.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-amber-400 flex items-center gap-1">
            <AlertTriangle size={11} /> Red flags
          </p>
          <ul className="space-y-1">
            {ai.red_flags.map((flag, i) => (
              <li key={i} className="text-xs text-amber-300/80 flex gap-2">
                <span className="mt-0.5">⚠</span>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function OfferEstimate({ listing }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [estimate, setEstimate] = useState(null)
  const [error, setError] = useState(null)

  async function load() {
    if (estimate) { setOpen(v => !v); return }
    setOpen(true)
    setLoading(true)
    setError(null)
    try {
      const data = await api.getOfferEstimate(listing)
      setEstimate(data)
      if (data.error && !data.logical && !data.ai) setError(data.error)
    } catch (e) {
      setError('Failed to load estimate. Try again.')
    } finally {
      setLoading(false)
    }
  }

  function openInCalculator() {
    const params = new URLSearchParams({ price: Math.round(listing.price) })
    navigate(`/mortgage?${params}`)
  }

  return (
    <div>
      <div className="flex items-center gap-3">
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs font-medium text-match-good hover:text-match-strong transition-colors py-1"
        >
          <Calculator size={12} />
          Estimate Offer
          {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        </button>
        {listing.price && (
          <button
            onClick={openInCalculator}
            className="flex items-center gap-1.5 text-xs font-medium text-amber-400/80 hover:text-amber-400 transition-colors py-1"
          >
            <Calculator size={12} />
            Mortgage Calc →
          </button>
        )}
      </div>

      {open && (
        <div className="mt-3 border border-canvas-600 rounded-xl bg-canvas-800/60 p-4 space-y-5">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-ink-muted py-2">
              <span className="animate-spin inline-block w-3.5 h-3.5 border-2 border-match-good border-t-transparent rounded-full" />
              Searching sold comps in this area…
            </div>
          )}

          {error && !loading && (
            <p className="text-xs text-red-400">{error}</p>
          )}

          {estimate && !loading && (
            <>
              {estimate.logical && (
                <LogicalSection logical={estimate.logical} listingPrice={listing.price} />
              )}
              {estimate.logical && estimate.ai && (
                <div className="border-t border-canvas-600" />
              )}
              {estimate.ai && <AISection ai={estimate.ai} />}
              {estimate.comps?.length > 0 && (
                <p className="text-xs text-ink-muted text-right">
                  {estimate.comps.length} sold comp{estimate.comps.length !== 1 ? 's' : ''} · up to 12 months · outliers removed
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
