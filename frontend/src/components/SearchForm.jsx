import { useState, useRef } from 'react'
import { api } from '../api'
import { Search, MapPin, Loader2 } from 'lucide-react'

const LISTING_TYPES = [
  { value: 'sale', label: 'Buy' },
  { value: 'rent', label: 'Rent' },
  { value: 'sold', label: 'Sold' },
  { value: 'coming_soon', label: 'Coming Soon' },
]

const PROPERTY_TYPES = [
  { value: 'single_family', label: 'House' },
  { value: 'condo', label: 'Condo' },
  { value: 'townhouse', label: 'Townhouse' },
  { value: 'multi_family', label: 'Multi-Family' },
  { value: 'commercial', label: 'Commercial' },
  { value: 'land', label: 'Land' },
]

const TRISTATE = [
  { value: null, label: "Don't care" },
  { value: true, label: 'Yes' },
  { value: false, label: 'No' },
]

export default function SearchForm({ onSearch, onLoading }) {
  const [criteria, setCriteria] = useState({
    location: '',
    radius_miles: 25,
    listing_type: 'sale',
    property_types: [],
    price_min: '',
    price_max: '',
    bedrooms_min: '',
    bathrooms_min: '',
    sqft_min: '',
    sqft_max: '',
    lot_sqft_min: '',
    lot_sqft_max: '',
    year_built_min: '',
    year_built_max: '',
    stories_min: '',
    has_basement: null,
    has_garage: null,
    garage_spaces_min: '',
    hoa_max: '',
    excluded_zips: [],
    zip_codes: [],
  })
  const [zipResults, setZipResults] = useState([])
  const [zipLoading, setZipLoading] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const debounceRef = useRef(null)
  const wrapperRef = useRef(null)

  const set = (field) => (e) => setCriteria({ ...criteria, [field]: e.target.value })
  const setNum = (field) => (e) => setCriteria({ ...criteria, [field]: e.target.value === '' ? '' : Number(e.target.value) })

  const discoverZips = async () => {
    if (!criteria.location) return
    setZipLoading(true)
    try {
      const data = await api.discoverZips(criteria.location, criteria.radius_miles)
      setZipResults(data.zips || [])
      setCriteria({ ...criteria, zip_codes: (data.zips || []).map(z => z.zipcode) })
    } catch (e) {
      console.error('ZIP discovery failed:', e)
    }
    setZipLoading(false)
  }

  const toggleZipExclude = (zip) => {
    const excluded = new Set(criteria.excluded_zips)
    if (excluded.has(zip)) {
      excluded.delete(zip)
    } else {
      excluded.add(zip)
    }
    setCriteria({ ...criteria, excluded_zips: [...excluded] })
  }

  const togglePropertyType = (pt) => {
    const types = new Set(criteria.property_types)
    if (types.has(pt)) {
      types.delete(pt)
    } else {
      types.add(pt)
    }
    setCriteria({ ...criteria, property_types: [...types] })
  }

  const buildCriteria = () => {
    const c = { ...criteria }
    // Convert empty strings to null for numeric fields
    for (const key of ['price_min', 'price_max', 'bedrooms_min', 'bathrooms_min',
      'sqft_min', 'sqft_max', 'lot_sqft_min', 'lot_sqft_max', 'year_built_min',
      'year_built_max', 'stories_min', 'garage_spaces_min', 'hoa_max']) {
      if (c[key] === '' || c[key] === undefined) c[key] = null
    }
    return c
  }

  const handleSearch = async (save = false) => {
    const c = buildCriteria()
    onSearch?.(c, save ? saveName : null)
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      {/* Location + Radius */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
          <div className="flex gap-2">
            <div className="relative flex-1" ref={wrapperRef}>
              <MapPin size={16} className="absolute left-3 top-2.5 text-gray-400" />
              <input
                type="text"
                placeholder="City, State or ZIP code"
                value={criteria.location}
                onChange={(e) => {
                  const val = e.target.value
                  setCriteria({ ...criteria, location: val })
                  clearTimeout(debounceRef.current)
                  if (val.length >= 3) {
                    debounceRef.current = setTimeout(async () => {
                      try {
                        const data = await api.searchLocations(val)
                        setSuggestions(data.suggestions || [])
                        setShowSuggestions(true)
                      } catch (_) {
                        setSuggestions([])
                      }
                    }, 300)
                  } else {
                    setSuggestions([])
                    setShowSuggestions(false)
                  }
                }}
                onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true) }}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                onKeyDown={(e) => { if (e.key === 'Escape') setShowSuggestions(false) }}
                className="w-full pl-9 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              {showSuggestions && suggestions.length > 0 && (
                <ul className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {suggestions.map((s, i) => (
                    <li
                      key={`${s.city}-${s.state}-${i}`}
                      onMouseDown={(e) => {
                        e.preventDefault()
                        setCriteria({ ...criteria, location: `${s.city}, ${s.state}` })
                        setShowSuggestions(false)
                        setSuggestions([])
                      }}
                      className="px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 flex items-center gap-2"
                    >
                      <MapPin size={14} className="text-gray-400 shrink-0" />
                      <span>{s.city}, <span className="text-gray-500">{s.state}</span></span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <button
              onClick={discoverZips}
              disabled={zipLoading || !criteria.location}
              className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 text-sm whitespace-nowrap"
            >
              {zipLoading ? <Loader2 size={16} className="animate-spin" /> : 'Preview ZIPs'}
            </button>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Radius (miles)</label>
          <select value={criteria.radius_miles} onChange={setNum('radius_miles')}
            className="w-full py-2 px-3 border rounded-lg">
            {[5, 10, 15, 25, 50, 100].map(r => <option key={r} value={r}>{r} miles</option>)}
          </select>
        </div>
      </div>

      {/* ZIP Discovery Results */}
      {zipResults.length > 0 && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600 mb-2">
            {zipResults.length} ZIP codes found. Click to exclude (red = excluded):
          </p>
          <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
            {zipResults.map(z => (
              <button
                key={z.zipcode}
                onClick={() => toggleZipExclude(z.zipcode)}
                className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                  criteria.excluded_zips.includes(z.zipcode)
                    ? 'bg-red-100 border-red-300 text-red-700 line-through'
                    : 'bg-white border-gray-200 text-gray-700 hover:bg-blue-50'
                }`}
                title={`${z.city}, ${z.state} (Pop: ${z.population?.toLocaleString() || 'N/A'})`}
              >
                {z.zipcode}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Listing type + Property type */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Looking to</label>
          <div className="flex gap-1">
            {LISTING_TYPES.map(lt => (
              <button
                key={lt.value}
                onClick={() => setCriteria({ ...criteria, listing_type: lt.value })}
                className={`flex-1 py-2 text-sm rounded-lg border transition-colors ${
                  criteria.listing_type === lt.value
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                }`}
              >
                {lt.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Property type</label>
          <div className="flex flex-wrap gap-1">
            {PROPERTY_TYPES.map(pt => (
              <button
                key={pt.value}
                onClick={() => togglePropertyType(pt.value)}
                className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                  criteria.property_types.includes(pt.value)
                    ? 'bg-blue-100 text-blue-700 border-blue-300'
                    : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                }`}
              >
                {pt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Price range */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Min Price</label>
          <input type="number" placeholder="No min" value={criteria.price_min}
            onChange={setNum('price_min')} className="w-full py-2 px-3 border rounded-lg" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Max Price</label>
          <input type="number" placeholder="No max" value={criteria.price_max}
            onChange={setNum('price_max')} className="w-full py-2 px-3 border rounded-lg" />
        </div>
      </div>

      {/* Beds / Baths */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Min Bedrooms</label>
          <select value={criteria.bedrooms_min} onChange={setNum('bedrooms_min')}
            className="w-full py-2 px-3 border rounded-lg">
            <option value="">Any</option>
            {[1,2,3,4,5,6].map(n => <option key={n} value={n}>{n}+</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Min Bathrooms</label>
          <select value={criteria.bathrooms_min} onChange={setNum('bathrooms_min')}
            className="w-full py-2 px-3 border rounded-lg">
            <option value="">Any</option>
            {[1,1.5,2,2.5,3,4].map(n => <option key={n} value={n}>{n}+</option>)}
          </select>
        </div>
      </div>

      {/* Advanced filters toggle */}
      <button
        onClick={() => setShowFilters(!showFilters)}
        className="text-sm text-blue-600 hover:text-blue-800 mb-4"
      >
        {showFilters ? '- Hide' : '+ Show'} advanced filters
      </button>

      {showFilters && (
        <div className="space-y-4 mb-4 p-4 bg-gray-50 rounded-lg">
          {/* Sq Footage */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Min Sq Ft</label>
              <input type="number" placeholder="Any" value={criteria.sqft_min}
                onChange={setNum('sqft_min')} className="w-full py-1.5 px-3 border rounded text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Max Sq Ft</label>
              <input type="number" placeholder="Any" value={criteria.sqft_max}
                onChange={setNum('sqft_max')} className="w-full py-1.5 px-3 border rounded text-sm" />
            </div>
          </div>

          {/* Lot size */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Min Lot (sqft)</label>
              <input type="number" placeholder="Any" value={criteria.lot_sqft_min}
                onChange={setNum('lot_sqft_min')} className="w-full py-1.5 px-3 border rounded text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Max Lot (sqft)</label>
              <input type="number" placeholder="Any" value={criteria.lot_sqft_max}
                onChange={setNum('lot_sqft_max')} className="w-full py-1.5 px-3 border rounded text-sm" />
            </div>
          </div>

          {/* Year built */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Built After</label>
              <input type="number" placeholder="Any" value={criteria.year_built_min}
                onChange={setNum('year_built_min')} className="w-full py-1.5 px-3 border rounded text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Built Before</label>
              <input type="number" placeholder="Any" value={criteria.year_built_max}
                onChange={setNum('year_built_max')} className="w-full py-1.5 px-3 border rounded text-sm" />
            </div>
          </div>

          {/* Stories */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Min Floors</label>
              <select value={criteria.stories_min} onChange={setNum('stories_min')}
                className="w-full py-1.5 px-3 border rounded text-sm">
                <option value="">Any</option>
                {[1,2,3].map(n => <option key={n} value={n}>{n}+</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Basement</label>
              <select
                value={criteria.has_basement === null ? '' : criteria.has_basement ? 'yes' : 'no'}
                onChange={(e) => setCriteria({
                  ...criteria,
                  has_basement: e.target.value === '' ? null : e.target.value === 'yes'
                })}
                className="w-full py-1.5 px-3 border rounded text-sm"
              >
                <option value="">Don't care</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Garage</label>
              <select
                value={criteria.has_garage === null ? '' : criteria.has_garage ? 'yes' : 'no'}
                onChange={(e) => setCriteria({
                  ...criteria,
                  has_garage: e.target.value === '' ? null : e.target.value === 'yes'
                })}
                className="w-full py-1.5 px-3 border rounded text-sm"
              >
                <option value="">Don't care</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
          </div>

          {/* HOA */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Max HOA ($/month)</label>
              <input type="number" placeholder="Any" value={criteria.hoa_max}
                onChange={setNum('hoa_max')} className="w-full py-1.5 px-3 border rounded text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Min Garage Spaces</label>
              <input type="number" placeholder="Any" value={criteria.garage_spaces_min}
                onChange={setNum('garage_spaces_min')} className="w-full py-1.5 px-3 border rounded text-sm" />
            </div>
          </div>
        </div>
      )}

      {/* Search + Save buttons */}
      <div className="flex gap-3 items-end">
        <button
          onClick={() => handleSearch(false)}
          disabled={!criteria.location}
          className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
        >
          <Search size={18} />
          Search
        </button>
        <div className="flex gap-2 items-end">
          <input
            type="text"
            placeholder="Search name..."
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            className="py-2.5 px-3 border rounded-lg text-sm w-40"
          />
          <button
            onClick={() => handleSearch(true)}
            disabled={!criteria.location || !saveName}
            className="px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm font-medium whitespace-nowrap"
          >
            Save & Search
          </button>
        </div>
      </div>
    </div>
  )
}
