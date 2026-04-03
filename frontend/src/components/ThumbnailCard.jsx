import { ExternalLink, Star } from 'lucide-react'

export default function ThumbnailCard({ listing }) {
  const price = listing.price
    ? listing.price >= 1000000
      ? `$${(listing.price / 1000000).toFixed(2)}M`
      : `$${Math.round(listing.price / 1000)}k`
    : null

  const beds = listing.bedrooms
  const baths = listing.bathrooms
  const dom = listing.days_on_mls

  // DOM badge color
  const domColor = dom == null ? null
    : dom < 7 ? 'bg-match-strong text-canvas-950'
    : dom <= 30 ? 'bg-canvas-700 text-ink-secondary'
    : dom <= 60 ? 'bg-match-warn/90 text-canvas-950'
    : 'bg-red-500/90 text-white'

  const domLabel = dom == null ? null
    : dom < 7 ? 'New'
    : dom <= 30 ? `${dom}d`
    : dom <= 60 ? `${dom}d`
    : `${dom}d`

  const handleClick = () => {
    if (listing.source_url) window.open(listing.source_url, '_blank', 'noopener')
  }

  return (
    <div
      onClick={handleClick}
      className={`relative rounded-xl overflow-hidden cursor-pointer group
        border transition-all duration-200
        ${listing.is_gold_star
          ? 'border-amber-500/60 shadow-glow-amber'
          : 'border-canvas-700 hover:border-canvas-500'
        }`}
      style={{ aspectRatio: '4/3' }}
    >
      {/* Photo */}
      {listing.photo_url ? (
        <img
          src={listing.photo_url}
          alt={listing.address}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-full bg-canvas-800 flex items-center justify-center">
          <span className="text-ink-muted text-3xl">🏠</span>
        </div>
      )}

      {/* Dark gradient overlay at bottom */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

      {/* Top-left: DOM badge */}
      {domLabel && (
        <div className={`absolute top-2 left-2 text-xs font-medium px-2 py-0.5 rounded-full ${domColor}`}>
          {domLabel}
        </div>
      )}

      {/* Top-right: Price */}
      {price && (
        <div className="absolute top-2 right-2 bg-amber-500 text-canvas-950 text-sm font-bold px-2.5 py-0.5 rounded-full shadow-lg">
          {price}
        </div>
      )}

      {/* Gold star */}
      {listing.is_gold_star && (
        <div className="absolute top-2 right-2 mt-7">
          <Star size={14} className="text-amber-400 fill-amber-400" />
        </div>
      )}

      {/* Bottom: address + bed/bath */}
      <div className="absolute bottom-0 left-0 right-0 p-2.5">
        <p className="text-white text-xs font-medium truncate leading-tight mb-1">
          {listing.address?.split(',')[0]}
        </p>
        <div className="flex items-center gap-2 text-white/80 text-xs">
          {beds && <span>{beds} bd</span>}
          {baths && <span>{baths} ba</span>}
          {listing.sqft && <span>{listing.sqft.toLocaleString()} sqft</span>}
          <div className="ml-auto">
            <ExternalLink size={11} className="opacity-60" />
          </div>
        </div>
      </div>
    </div>
  )
}
