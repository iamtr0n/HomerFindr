import { useState } from 'react'
import { ExternalLink, Bed, Bath, Ruler, Calendar, Home } from 'lucide-react'
import { Card, CardContent } from './ui/Card'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'

export default function PropertyCard({ listing, isGoldStar = false }) {
  const {
    address, city, state, price, bedrooms, bathrooms, sqft, year_built,
    has_garage, has_basement, stories, hoa_monthly, photo_url, source_url,
    source, zip_code, property_type, match_badges,
  } = listing

  const [imgLoaded, setImgLoaded] = useState(false)
  const placeholderClass = `w-full h-52 bg-slate-100 flex flex-col items-center justify-center text-slate-400 gap-2${photo_url && !imgLoaded ? ' animate-pulse' : ''}`

  const priceStr = price ? `$${price.toLocaleString()}` : 'Price N/A'

  const features = []
  if (has_garage) features.push('Garage')
  if (has_basement) features.push('Basement')
  if (stories) features.push(`${stories} Floor${stories > 1 ? 's' : ''}`)
  if (hoa_monthly) features.push(`HOA $${hoa_monthly}/mo`)

  const locationStr = [city, state].filter(Boolean).join(', ')
  const fullLocation = [locationStr, zip_code].filter(Boolean).join(' ')

  return (
    <Card className={`overflow-hidden hover:shadow-md transition-shadow ${isGoldStar ? 'ring-2 ring-amber-400 border-amber-300' : ''}`}>
      {/* Photo */}
      <a href={source_url || '#'} target="_blank" rel="noopener noreferrer" className="relative block">
        {photo_url ? (
          <img
            src={photo_url}
            alt={address}
            className="w-full h-52 object-cover bg-slate-100"
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
          className={placeholderClass}
          style={photo_url && imgLoaded ? { display: 'none' } : undefined}
        >
          <Home size={28} />
          <span className="text-xs">No Photo Available</span>
        </div>
        {isGoldStar && (
          <Badge className="absolute top-2 left-2 bg-amber-400 text-amber-900 shadow-sm">
            &#11088; Perfect Match
          </Badge>
        )}
        <Badge variant="secondary" className="absolute top-2 right-2 capitalize shadow-sm">
          {source}
        </Badge>
      </a>

      <CardContent className="p-4">
        {/* Price */}
        <p className="text-2xl font-bold text-slate-900 mb-1">{priceStr}</p>

        {/* Stats row */}
        <div className="flex items-center gap-3 text-sm text-slate-600 mb-2">
          {bedrooms != null && (
            <span className="flex items-center gap-1"><Bed size={14} /> {bedrooms} bd</span>
          )}
          {bathrooms != null && (
            <span className="flex items-center gap-1"><Bath size={14} /> {bathrooms} ba</span>
          )}
          {sqft != null && (
            <span className="flex items-center gap-1"><Ruler size={14} /> {sqft.toLocaleString()} sqft</span>
          )}
          {year_built != null && (
            <span className="flex items-center gap-1"><Calendar size={14} /> {year_built}</span>
          )}
        </div>

        {/* Address */}
        <p className="text-sm text-slate-500 line-clamp-1 mb-2">{address}</p>
        {fullLocation && (
          <p className="text-xs text-slate-400 mb-3">{fullLocation}</p>
        )}

        {/* Match badges */}
        {match_badges && match_badges.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {match_badges.map((badge) => (
              <span key={badge} className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                {badge}
              </span>
            ))}
          </div>
        )}

        {/* Features */}
        {features.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {features.map((f) => (
              <Badge key={f} variant="outline" className="text-xs">{f}</Badge>
            ))}
          </div>
        )}

        {/* Property type */}
        <div className="flex justify-between items-center text-xs text-slate-400 mb-3">
          <span className="capitalize">{(property_type || '').replace('_', ' ')}</span>
        </div>

        {/* View link */}
        {source_url && (
          <a href={source_url} target="_blank" rel="noopener noreferrer" className="block">
            <Button variant="default" className="w-full">
              <ExternalLink size={14} /> View on {source}
            </Button>
          </a>
        )}
      </CardContent>
    </Card>
  )
}
