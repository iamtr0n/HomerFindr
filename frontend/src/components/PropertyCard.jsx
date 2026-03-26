import { useState } from 'react'
import { ExternalLink, Bed, Bath, Ruler, Calendar, Home } from 'lucide-react'
import { Card, CardContent } from './ui/Card'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'

const LISTING_TYPE_STYLES = {
  sale: { label: 'For Sale', cls: 'bg-green-100 text-green-800 border-green-300' },
  pending: { label: 'Pending', cls: 'bg-amber-100 text-amber-800 border-amber-300' },
  coming_soon: { label: 'Coming Soon', cls: 'bg-blue-100 text-blue-800 border-blue-300' },
  rent: { label: 'For Rent', cls: 'bg-purple-100 text-purple-800 border-purple-300' },
  sold: { label: 'Sold', cls: 'bg-gray-100 text-gray-600 border-gray-300' },
}

function DomBadge({ days }) {
  if (days == null) return null
  if (days < 7) return (
    <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 border border-green-300 font-medium">New</span>
  )
  if (days >= 31 && days <= 60) return (
    <span className="px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-700 border border-amber-300">{days} days</span>
  )
  if (days > 60) return (
    <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700 border border-red-300">{days} days</span>
  )
  return null
}

export default function PropertyCard({ listing, isGoldStar = false }) {
  const {
    address, city, state, price, bedrooms, bathrooms, sqft, year_built,
    has_garage, has_basement, stories, hoa_monthly, photo_url, source_url,
    source, zip_code, property_type, match_badges, near_highway, highway_name,
    school_rating, school_district, listing_type, match_score, days_on_mls,
  } = listing

  const [imgLoaded, setImgLoaded] = useState(false)
  const placeholderClass = `w-full h-52 bg-slate-100 flex flex-col items-center justify-center text-slate-400 gap-2${photo_url && !imgLoaded ? ' animate-pulse' : ''}`

  const priceStr = price ? `$${price.toLocaleString()}` : 'Price N/A'

  const features = []
  if (has_garage) features.push('Garage')
  if (has_basement) features.push('Basement')
  if (stories) features.push(`${stories} Floor${stories > 1 ? 's' : ''}`)
  if (hoa_monthly) features.push(`HOA $${hoa_monthly}/mo`)
  if (school_rating) features.push(`School: ${school_rating}/10`)

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
        {/* Listing type badge — bottom-left of image */}
        {listing_type && LISTING_TYPE_STYLES[listing_type] && (
          <span className={`absolute bottom-2 left-2 px-2 py-0.5 text-xs rounded-full border font-medium shadow-sm ${LISTING_TYPE_STYLES[listing_type].cls}`}>
            {LISTING_TYPE_STYLES[listing_type].label}
          </span>
        )}
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
        {/* Price + score chip */}
        <div className="flex items-baseline gap-2 mb-1">
          <p className="text-2xl font-bold text-slate-900">{priceStr}</p>
          {match_score != null && match_score > 0 && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-medium">
              {match_score} match
            </span>
          )}
          <DomBadge days={days_on_mls} />
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-3 text-sm text-slate-600 mb-2 flex-wrap">
          {bedrooms != null && (
            <span className="flex items-center gap-1"><Bed size={14} /> {bedrooms} bd</span>
          )}
          {bathrooms != null && (
            <span className="flex items-center gap-1"><Bath size={14} /> {bathrooms} ba</span>
          )}
          {sqft != null && (
            <span className="flex items-center gap-1"><Ruler size={14} /> {sqft.toLocaleString()} sqft</span>
          )}
          {price != null && sqft != null && sqft > 0 && (
            <span className="text-slate-400">${Math.round(price / sqft).toLocaleString()}/sqft</span>
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

        {/* Highway warning */}
        {near_highway && (
          <div className="flex items-center gap-1 text-amber-600 text-xs font-medium mb-2">
            <span>&#9888;&#65039;</span> Near {highway_name || 'Highway'}
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
