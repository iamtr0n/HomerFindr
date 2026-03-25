import { ExternalLink, Bed, Bath, Ruler, Calendar, Car, ArrowDown } from 'lucide-react'

export default function PropertyCard({ listing }) {
  const {
    address, price, bedrooms, bathrooms, sqft, lot_sqft, year_built,
    has_garage, has_basement, stories, hoa_monthly, photo_url, source_url,
    source, zip_code, property_type,
  } = listing

  const priceStr = price ? `$${price.toLocaleString()}` : 'Price N/A'

  const features = []
  if (has_garage) features.push('Garage')
  if (has_basement) features.push('Basement')
  if (stories) features.push(`${stories} Floor${stories > 1 ? 's' : ''}`)
  if (hoa_monthly) features.push(`HOA $${hoa_monthly}/mo`)

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
      {/* Photo */}
      <a href={source_url || '#'} target="_blank" rel="noopener noreferrer" className="block">
        {photo_url ? (
          <img
            src={photo_url}
            alt={address}
            className="w-full h-48 object-cover bg-gray-200"
            onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex' }}
          />
        ) : null}
        <div className={`w-full h-48 bg-gray-200 items-center justify-center text-gray-400 ${photo_url ? 'hidden' : 'flex'}`}>
          No Photo Available
        </div>
      </a>

      <div className="p-4">
        {/* Price */}
        <div className="flex justify-between items-start mb-1">
          <span className="text-xl font-bold text-green-600">{priceStr}</span>
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded capitalize">
            {source}
          </span>
        </div>

        {/* Address */}
        <h3 className="text-sm font-medium text-gray-800 mb-2 line-clamp-2">{address}</h3>

        {/* Key stats */}
        <div className="flex gap-3 text-sm text-gray-600 mb-2">
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

        {/* Features */}
        {features.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {features.map((f) => (
              <span key={f} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">{f}</span>
            ))}
          </div>
        )}

        {/* Property type + ZIP */}
        <div className="flex justify-between items-center text-xs text-gray-400 mt-2">
          <span className="capitalize">{(property_type || '').replace('_', ' ')}</span>
          <span>{zip_code}</span>
        </div>

        {/* View link */}
        {source_url && (
          <a
            href={source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 w-full flex items-center justify-center gap-1.5 text-sm bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition-colors"
          >
            <ExternalLink size={14} /> View on {source}
          </a>
        )}
      </div>
    </div>
  )
}
