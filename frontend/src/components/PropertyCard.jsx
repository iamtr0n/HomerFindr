import { useState, useCallback } from 'react'
import { ExternalLink, Bed, Bath, Ruler, Calendar, Home, Bookmark, X } from 'lucide-react'
import OfferEstimate from './OfferEstimate'

const LISTING_TYPE_STYLES = {
  sale:        { label: 'For Sale',    cls: 'bg-match-strong/70 text-white border border-match-strong' },
  pending:     { label: 'Pending',     cls: 'bg-amber-500/20 text-amber-400 border border-amber-500/40' },
  coming_soon: { label: 'Coming Soon', cls: 'bg-match-good/20 text-match-good border border-match-good/40' },
  rent:        { label: 'For Rent',    cls: 'bg-purple-400/20 text-purple-400 border border-purple-400/40' },
  sold:        { label: 'Sold',        cls: 'bg-canvas-600 text-ink-muted border border-canvas-500' },
}

function DomBadge({ days }) {
  if (days == null) return null
  const label = days === 0 ? 'Listed today' : days === 1 ? '1 day on market' : `${days} days on market`
  if (days <= 14) return (
    <p className="text-xs font-medium">
      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 border border-green-500/30">{label}</span>
    </p>
  )
  if (days <= 45) return (
    <p className="text-xs font-medium">
      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">{label}</span>
    </p>
  )
  return (
    <p className="text-xs font-medium">
      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">{label}</span>
    </p>
  )
}

function MatchDots({ score, maxScore }) {
  const filled = maxScore > 0 ? Math.round((score / maxScore) * 5) : 0
  return (
    <div className="flex items-center gap-0.5">
      {[...Array(5)].map((_, i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i < filled ? 'bg-amber-400' : 'bg-canvas-600'}`}
        />
      ))}
    </div>
  )
}

const VIEWED_KEY = 'homerfindr_viewed'
function readViewed() {
  try { return new Set(JSON.parse(localStorage.getItem(VIEWED_KEY) || '[]')) } catch { return new Set() }
}
function writeViewed(set) {
  try { localStorage.setItem(VIEWED_KEY, JSON.stringify([...set])) } catch {}
}

const DISMISSED_KEY = 'homerfindr_dismissed'
function readDismissed() {
  try { return new Set(JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]')) } catch { return new Set() }
}
function writeDismissed(set) {
  try { localStorage.setItem(DISMISSED_KEY, JSON.stringify([...set])) } catch {}
}

export default function PropertyCard({ listing, isGoldStar = false, isViewed = false, maxScore = 5, onToggleStar, mortgageSettings, onDismiss, commuteMinutes }) {
  const {
    id: listingId, address, city, state, price, list_price, bedrooms, bathrooms, sqft, year_built,
    has_garage, has_basement, stories, hoa_monthly, photo_url, source_url,
    source, zip_code, property_type, match_badges, near_highway, highway_name,
    school_rating, listing_type, match_score, days_on_mls, source_id, is_starred,
    price_change, is_new,
  } = listing

  const [imgLoaded, setImgLoaded] = useState(false)
  const [viewed, setViewed] = useState(() => source_id ? readViewed().has(source_id) : false)
  const [starred, setStarred] = useState(is_starred || false)
  // Optimistic local hide — parent handles actual persistence via API
  const [hidden, setHidden] = useState(false)

  const handleDismiss = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!source_id) return
    setHidden(true)
    onDismiss?.(source_id)
  }, [source_id, onDismiss])

  const markViewed = useCallback(() => {
    if (!source_id || viewed) return
    const set = readViewed()
    set.add(source_id)
    writeViewed(set)
    setViewed(true)
  }, [source_id, viewed])

  if (hidden) return null

  // Mortgage monthly payment
  let monthlyPayment = null
  if (mortgageSettings && price) {
    const { rate, downPct, termYears } = mortgageSettings
    const principal = price * (1 - downPct / 100)
    const r = rate / 100 / 12
    const n = termYears * 12
    if (r > 0 && n > 0 && principal > 0) {
      monthlyPayment = Math.round(principal * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1))
    }
  }

  // Price change badge
  let priceChangeBadge = null
  if (price_change && price_change.delta != null) {
    const isDown = price_change.delta < 0
    const absDelta = Math.abs(price_change.delta)
    const deltaStr = absDelta >= 1000 ? `$${Math.round(absDelta / 1000)}k` : `$${Math.round(absDelta)}`
    const daysAgo = price_change.changed_at
      ? Math.max(0, Math.floor((Date.now() - new Date(price_change.changed_at).getTime()) / 86400000))
      : null
    const timeStr = daysAgo === 0 ? 'today' : daysAgo === 1 ? '1 day ago' : daysAgo != null ? `${daysAgo}d ago` : ''
    priceChangeBadge = { isDown, deltaStr, timeStr }
  }

  const isViewedState = isViewed || viewed
  const priceStr = price ? `$${price.toLocaleString()}` : 'Price N/A'
  const priceSqft = price && sqft && sqft > 0 ? Math.round(price / sqft) : null
  const locationStr = [city, state].filter(Boolean).join(', ')
  const fullLocation = [locationStr, zip_code].filter(Boolean).join(' ')

  const features = []
  if (has_garage) features.push('Garage')
  if (has_basement) features.push('Basement')
  if (stories) features.push(`${stories} Floor${stories > 1 ? 's' : ''}`)
  if (hoa_monthly) features.push(`HOA $${hoa_monthly}/mo`)
  if (school_rating) features.push(`Schools ${school_rating}/10`)

  return (
    <div className={`
      rounded-xl border bg-canvas-900 overflow-hidden transition-all duration-200
      hover:shadow-card-hover hover:border-canvas-500
      ${isGoldStar ? 'border-amber-500/50 shadow-glow-amber' : 'border-canvas-700 shadow-card'}
      ${isViewedState ? 'opacity-60 grayscale-[20%]' : ''}
    `}>
      {/* Photo */}
      <a
        href={source_url || '#'}
        target="_blank"
        rel="noopener noreferrer"
        className="relative block group"
        onClick={markViewed}
      >
        {photo_url ? (
          <img
            src={photo_url}
            alt={address}
            className="w-full h-48 object-cover bg-canvas-800"
            referrerPolicy="no-referrer"
            onLoad={() => setImgLoaded(true)}
            onError={(e) => {
              e.target.style.display = 'none'
              e.target.nextSibling.style.display = 'flex'
              setImgLoaded(true)
            }}
          />
        ) : null}
        <div
          className={`w-full h-48 bg-canvas-800 flex flex-col items-center justify-center text-canvas-500 gap-2${photo_url && !imgLoaded ? ' animate-pulse' : ''}`}
          style={photo_url && imgLoaded ? { display: 'none' } : undefined}
        >
          <Home size={28} />
          <span className="text-xs text-canvas-600">No Photo</span>
        </div>

        {/* Dismiss button — large touch target, always visible on mobile */}
        {source_id && (
          <button
            onClick={handleDismiss}
            title="Hide this listing"
            className="absolute top-1.5 left-1.5 z-10 w-10 h-10 flex items-center justify-center bg-canvas-900/70 backdrop-blur-sm rounded-full border border-canvas-500/60 text-ink-secondary hover:bg-red-500 hover:border-red-500 hover:text-white sm:opacity-50 sm:hover:opacity-100 opacity-90 transition-all duration-150 active:scale-95"
          >
            <X size={17} />
          </button>
        )}

        {/* New listing badge — left-14 to clear the 40px dismiss button */}
        {is_new && !isGoldStar && (
          <span className="absolute top-2 left-14 bg-match-strong text-white font-semibold text-xs rounded-full px-3 py-1 shadow-sm">
            New
          </span>
        )}

        {/* Gold star badge */}
        {isGoldStar && (
          <span className="absolute top-2 left-14 bg-amber-500 text-canvas-950 font-semibold text-xs rounded-full px-3 py-1">
            {is_new ? '⭐ New · Perfect Match' : '⭐ Perfect Match'}
          </span>
        )}

        {/* Source badge */}
        <span className="absolute top-2 right-2 bg-canvas-900/80 backdrop-blur-sm text-ink-muted text-xs rounded-full px-2.5 py-0.5 capitalize border border-canvas-700">
          {source}
        </span>

        {/* Listing type badge */}
        {listing_type && LISTING_TYPE_STYLES[listing_type] && (
          <span className={`absolute bottom-2 left-2 px-2.5 py-0.5 text-xs rounded-full font-medium ${LISTING_TYPE_STYLES[listing_type].cls}`}>
            {LISTING_TYPE_STYLES[listing_type].label}
          </span>
        )}

        {/* Viewed badge */}
        {isViewedState && (
          <span className="absolute bottom-2 right-2 bg-canvas-800/90 text-ink-muted text-xs rounded-full px-2 py-0.5 border border-canvas-600">
            Viewed
          </span>
        )}
      </a>

      {/* Content */}
      <div className="p-4">
        {/* Days on market — right below the photo */}
        {days_on_mls != null && <div className="mb-2"><DomBadge days={days_on_mls} /></div>}

        {/* Price row */}
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <p className="font-serif text-2xl text-ink-primary">
                {listing_type === 'sold' && price ? `$${price.toLocaleString()}` : priceStr}
              </p>
              {listing_type === 'sold' && price && (
                <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-canvas-700 text-ink-muted">SOLD</span>
              )}
            </div>
            {listing_type === 'sold' && list_price && (
              <p className="text-xs text-ink-muted mt-0.5">
                Asked <span className="font-mono">${list_price.toLocaleString()}</span>
                {price && list_price && (
                  <span className={`ml-1.5 font-medium ${price > list_price ? 'text-red-400' : 'text-green-400'}`}>
                    ({price > list_price ? '+' : ''}{Math.round((price - list_price) / list_price * 100)}% {price > list_price ? 'over' : 'under'} ask)
                  </span>
                )}
              </p>
            )}
          </div>
          {match_score != null && match_score > 0 && (
            <MatchDots score={match_score} maxScore={maxScore} />
          )}
          {priceChangeBadge && (
            <span className={`px-2 py-0.5 text-xs rounded-full font-medium border ${
              priceChangeBadge.isDown
                ? 'bg-match-strong/10 text-match-strong border-match-strong/30'
                : 'bg-red-400/10 text-red-400 border-red-400/30'
            }`}>
              {priceChangeBadge.isDown ? '↓' : '↑'} {priceChangeBadge.deltaStr}
              {priceChangeBadge.timeStr && <span className="opacity-70"> · {priceChangeBadge.timeStr}</span>}
            </span>
          )}
        </div>
        {monthlyPayment && (
          <p className={`text-xs mb-1 ${
            !mortgageSettings?.budgetMax ? 'text-ink-muted'
            : monthlyPayment <= mortgageSettings.budgetMax ? 'text-match-strong'
            : monthlyPayment <= mortgageSettings.budgetMax * 1.2 ? 'text-match-warn'
            : 'text-red-400'
          }`}>~${monthlyPayment.toLocaleString()}/mo</p>
        )}
        {commuteMinutes != null && (
          <p className="text-xs text-ink-muted mb-1">
            ~{commuteMinutes} min to work
            <span className={`ml-1 font-medium ${commuteMinutes <= 20 ? 'text-match-strong' : commuteMinutes <= 40 ? 'text-match-warn' : 'text-red-400'}`}>
              ●
            </span>
          </p>
        )}

        {/* Stats row */}
        <div className="flex items-center gap-3 text-sm text-ink-secondary mb-2 flex-wrap">
          {bedrooms != null && <span className="flex items-center gap-1"><Bed size={13} /> {bedrooms} bd</span>}
          {bathrooms != null && <span className="flex items-center gap-1"><Bath size={13} /> {bathrooms} ba</span>}
          {sqft != null && <span className="flex items-center gap-1"><Ruler size={13} /> {sqft.toLocaleString()}</span>}
          {priceSqft && <span className="text-ink-muted font-mono text-xs">${priceSqft.toLocaleString()}/sqft</span>}
          {year_built != null && <span className="flex items-center gap-1 text-ink-muted"><Calendar size={13} /> {year_built}</span>}
        </div>

        {/* Address */}
        <p className="text-sm text-ink-secondary line-clamp-1 mb-0.5">{address}</p>
        {fullLocation && <p className="text-xs text-ink-muted mb-3">{fullLocation}</p>}

        {/* Match badges */}
        {match_badges && match_badges.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {match_badges.map(badge => (
              <span key={badge} className="px-2 py-0.5 text-xs rounded-full bg-match-good/10 text-match-good border border-match-good/20">
                {badge}
              </span>
            ))}
          </div>
        )}

        {/* Highway warning */}
        {near_highway && (
          <div className="flex items-center gap-1.5 text-match-warn text-xs font-medium mb-2">
            <span>⚠</span> Near {highway_name || 'Highway'}
          </div>
        )}

        {/* Feature pills */}
        {features.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {features.map(f => (
              <span key={f} className="px-2.5 py-0.5 text-xs rounded-full border border-canvas-600 text-ink-muted bg-canvas-800">
                {f}
              </span>
            ))}
          </div>
        )}

        {/* Property type */}
        <p className="text-xs text-canvas-500 capitalize mb-3">{(property_type || '').replace('_', ' ')}</p>

        {/* Offer estimate */}
        {(listing_type === 'sale' || listing_type === 'pending') && listing.price && (
          <div className="mb-3">
            <OfferEstimate listing={listing} />
          </div>
        )}

        {/* View + Save row */}
        <div className="flex gap-2">
          {source_url ? (
            <a href={source_url} target="_blank" rel="noopener noreferrer" onClick={markViewed} className="flex-1">
              <button className="w-full flex items-center justify-center gap-2 bg-canvas-800 border border-canvas-600 hover:border-amber-500 hover:text-amber-400 text-ink-secondary text-sm rounded-lg py-2 transition-all duration-150">
                <ExternalLink size={14} /> View on {source}
              </button>
            </a>
          ) : (
            <div className="flex-1 h-9" />
          )}
          {onToggleStar && listingId && (
            <button
              onClick={() => { setStarred(s => !s); onToggleStar(listingId) }}
              title={starred ? 'Unsave' : 'Save listing'}
              className={`px-3 rounded-lg border transition-all duration-150 ${
                starred
                  ? 'bg-amber-500/15 border-amber-500/40 text-amber-400'
                  : 'bg-canvas-800 border-canvas-600 text-ink-muted hover:border-amber-500 hover:text-amber-400'
              }`}
            >
              <Bookmark size={14} className={starred ? 'fill-current' : ''} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
