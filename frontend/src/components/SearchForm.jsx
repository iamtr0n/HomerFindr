import { useState, useRef, useEffect } from 'react'
import { api } from '../api'
import { Search, MapPin, Loader2, Map, X } from 'lucide-react'
import PriceRangeSlider from './PriceRangeSlider'
import ListingMap from './ListingMap'
import { useMortgage } from './MortgageBar'

const LISTING_TYPES = [
  { value: 'sale', label: 'Buy' },
  { value: 'pending', label: 'Pending' },
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

const HOUSE_STYLES = [
  { value: 'split_level',   label: 'Split Level' },
  { value: 'ranch',         label: 'Ranch' },
  { value: 'raised_ranch',  label: 'Raised Ranch' },
  { value: 'colonial',      label: 'Colonial' },
  { value: 'cape_cod',      label: 'Cape Cod' },
  { value: 'craftsman',     label: 'Craftsman' },
  { value: 'contemporary',  label: 'Contemporary' },
  { value: 'tudor',         label: 'Tudor' },
  { value: 'victorian',     label: 'Victorian' },
  { value: 'traditional',   label: 'Traditional' },
]

const BEDS_OPTIONS = [
  { value: null, label: 'Any' },
  { value: 1, label: '1+' },
  { value: 2, label: '2+' },
  { value: 3, label: '3+' },
  { value: 4, label: '4+' },
  { value: 5, label: '5+' },
]

const BATHS_OPTIONS = [
  { value: null, label: 'Any' },
  { value: 1, label: '1+' },
  { value: 1.5, label: '1.5+' },
  { value: 2, label: '2+' },
  { value: 3, label: '3+' },
]

const STORIES_OPTIONS = [
  { value: null, label: 'Any' },
  { value: 1, label: '1' },
  { value: 2, label: '2' },
  { value: 3, label: '3' },
  { value: 4, label: '4+' },
]

const TRISTATE = [
  { value: null, label: 'Any' },
  { value: true, label: 'Yes' },
  { value: false, label: 'No' },
]

const inputCls = 'w-full bg-canvas-800 border border-canvas-600 text-ink-primary placeholder:text-ink-muted rounded-lg py-2 px-3 text-sm focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/30 transition-colors'
const labelCls = 'block text-xs font-medium text-ink-muted uppercase tracking-widest mb-1.5'

function BtnGroup({ options, value, onChange, multi = false }) {
  const isActive = (opt) => {
    if (multi) return Array.isArray(value) && value.includes(opt.value)
    return value === opt.value
  }

  const handleClick = (opt) => {
    if (multi) {
      const arr = Array.isArray(value) ? value : []
      if (arr.includes(opt.value)) {
        if (arr.length === 1) return
        onChange(arr.filter(v => v !== opt.value))
      } else {
        onChange([...arr, opt.value])
      }
    } else {
      onChange(opt.value)
    }
  }

  return (
    <div className="flex gap-1 flex-wrap">
      {options.map((opt, i) => (
        <button
          key={i}
          type="button"
          onClick={() => handleClick(opt)}
          className={`px-2.5 py-1 text-xs rounded-lg border transition-all ${
            isActive(opt)
              ? 'bg-amber-500/20 border-amber-500 text-amber-400 font-medium'
              : 'bg-canvas-800 border-canvas-600 text-ink-secondary hover:border-canvas-500 hover:text-ink-primary'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

export default function SearchForm({ onSearch, onLoading, initialZipCodes, initialCriteria, searchName }) {
  const _init = initialCriteria || {}
  const { settings: mortgage } = useMortgage()
  const [listingTypes, setListingTypes] = useState(_init.listing_types || ['sale'])
  const [criteria, setCriteria] = useState({
    location: '', radius_miles: 25, property_types: [], house_styles: [], style_strict: false,
    bedrooms_min: null, bathrooms_min: null,
    sqft_min: '', sqft_max: '', lot_sqft_min: '', lot_sqft_max: '',
    year_built_min: '', stories_min: null,
    has_basement: null, has_garage: null,
    has_pool: null, has_fireplace: null, has_ac: null,
    garage_spaces_min: '',
    hoa_max: '', excluded_zips: [], zip_codes: [],
    avoid_highways: false, school_rating_min: '',
    ..._init,
  })

  useEffect(() => {
    if (initialZipCodes && initialZipCodes.length > 0) {
      setCriteria(prev => ({ ...prev, zip_codes: initialZipCodes }))
    }
  }, [initialZipCodes])
  const [priceMin, setPriceMin] = useState(_init.price_min || null)
  const [priceMax, setPriceMax] = useState(_init.price_max || null)
  const [maxMonthlyPayment, setMaxMonthlyPayment] = useState('')
  const [zipResults, setZipResults] = useState([])
  const [zipLoading, setZipLoading] = useState(false)
  const [polygonMode, setPolygonMode] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [showMapDraw, setShowMapDraw] = useState(false)
  const [mapDrawLoading, setMapDrawLoading] = useState(false)
  const [saveName, setSaveName] = useState(searchName || '')
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const debounceRef = useRef(null)
  const wrapperRef = useRef(null)

  const set = (field) => (e) => setCriteria({ ...criteria, [field]: e.target.value })
  const setNum = (field) => (e) => setCriteria({ ...criteria, [field]: e.target.value === '' ? '' : Number(e.target.value) })
  const setField = (field) => (val) => setCriteria({ ...criteria, [field]: val })

  const discoverZips = async () => {
    if (!criteria.location) return
    setZipLoading(true)
    try {
      const data = await api.discoverZips(criteria.location, criteria.radius_miles)
      setZipResults(data.zips || [])
      setCriteria(prev => ({ ...prev, zip_codes: (data.zips || []).map(z => z.zipcode) }))
    } catch (e) { console.error('ZIP discovery failed:', e) }
    setZipLoading(false)
  }

  const handlePolygonComplete = async (coords) => {
    setMapDrawLoading(true)
    try {
      const data = await api.zipFromPolygon(coords)
      const zips = data.zips || []
      setZipResults(zips)
      setCriteria(prev => ({
        ...prev,
        zip_codes: zips.map(z => z.zipcode),
        location: prev.location || 'Map selection',
      }))
      setPolygonMode(true)
      setShowMapDraw(false)
    } catch (e) {
      console.error('Polygon ZIP lookup failed:', e)
    }
    setMapDrawLoading(false)
  }

  const toggleZipExclude = (zip) => {
    setCriteria(prev => {
      const excluded = new Set(prev.excluded_zips)
      if (excluded.has(zip)) excluded.delete(zip)
      else excluded.add(zip)
      return { ...prev, excluded_zips: [...excluded] }
    })
  }

  const toggleHouseStyle = (style) => {
    setCriteria(prev => {
      const styles = new Set(prev.house_styles)
      if (styles.has(style)) styles.delete(style)
      else styles.add(style)
      return { ...prev, house_styles: [...styles] }
    })
  }

  const togglePropertyType = (pt) => {
    setCriteria(prev => {
      const types = new Set(prev.property_types)
      if (types.has(pt)) types.delete(pt)
      else types.add(pt)
      return { ...prev, property_types: [...types] }
    })
  }

  const buildCriteria = () => {
    const c = { ...criteria }
    c.listing_types = listingTypes
    c.price_min = priceMin
    c.price_max = priceMax
    for (const key of ['sqft_min', 'sqft_max', 'lot_sqft_min', 'lot_sqft_max',
      'year_built_min', 'garage_spaces_min', 'hoa_max', 'school_rating_min']) {
      if (c[key] === '' || c[key] === undefined) c[key] = null
    }
    return c
  }

  const handleSearch = async (save = false) => {
    const c = buildCriteria()
    onSearch?.(c, save ? saveName : null)
  }

  return (
    <div className="bg-canvas-900 border border-canvas-700 rounded-xl p-4 space-y-3">
      {/* Location */}
      <div>
        <label className={labelCls}>Location</label>
        <div className="flex gap-2">
          <div className="relative flex-1" ref={wrapperRef}>
            <MapPin size={15} className="absolute left-3 top-2.5 text-ink-muted pointer-events-none" />
            <input
              type="text"
              placeholder="City, State or ZIP"
              value={criteria.location}
              onChange={(e) => {
                const val = e.target.value
                setCriteria({ ...criteria, location: val })
                if (polygonMode) setPolygonMode(false)
                clearTimeout(debounceRef.current)
                if (val.length >= 3) {
                  debounceRef.current = setTimeout(async () => {
                    try {
                      const data = await api.searchLocations(val)
                      setSuggestions(data.suggestions || [])
                      setShowSuggestions(true)
                    } catch { setSuggestions([]) }
                  }, 300)
                } else {
                  setSuggestions([])
                  setShowSuggestions(false)
                }
              }}
              onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true) }}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              onKeyDown={(e) => { if (e.key === 'Escape') setShowSuggestions(false) }}
              className={`${inputCls} pl-9`}
            />
            {showSuggestions && suggestions.length > 0 && (
              <ul className="absolute z-50 top-full left-0 right-0 mt-1 bg-canvas-800 border border-canvas-600 rounded-lg shadow-card-hover max-h-48 overflow-y-auto">
                {suggestions.map((s, i) => (
                  <li
                    key={`${s.city}-${s.state}-${i}`}
                    onMouseDown={(e) => {
                      e.preventDefault()
                      setCriteria({ ...criteria, location: `${s.city}, ${s.state}` })
                      setShowSuggestions(false)
                      setSuggestions([])
                    }}
                    className="px-3 py-2 text-sm cursor-pointer hover:bg-canvas-700 flex items-center gap-2 text-ink-secondary"
                  >
                    <MapPin size={13} className="text-ink-muted shrink-0" />
                    <span>{s.city}, <span className="text-ink-muted">{s.state}</span></span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            onClick={discoverZips}
            disabled={zipLoading || !criteria.location}
            className="px-3 py-2 bg-canvas-800 border border-canvas-600 text-ink-secondary rounded-lg hover:border-canvas-500 disabled:opacity-50 text-xs whitespace-nowrap transition-colors"
          >
            {zipLoading ? <Loader2 size={14} className="animate-spin" /> : 'Preview ZIPs'}
          </button>
          <button
            type="button"
            onClick={() => setShowMapDraw(true)}
            title="Draw search area on map"
            className="px-3 py-2 bg-canvas-800 border border-canvas-600 text-ink-secondary rounded-lg hover:border-amber-500 hover:text-amber-400 text-xs whitespace-nowrap transition-colors flex items-center gap-1.5"
          >
            <Map size={13} /> Draw Area
          </button>
        </div>
      </div>

      {/* Radius — hidden when area was drawn on map */}
      {!polygonMode && <div>
        <label className={labelCls}>Search Radius — <span className="text-ink-primary font-semibold">{criteria.radius_miles} mi</span></label>
        <input
          type="range"
          min={1}
          max={25}
          step={1}
          value={criteria.radius_miles}
          onChange={(e) => setCriteria({ ...criteria, radius_miles: Number(e.target.value) })}
          className="w-full cursor-pointer"
        />
        <div className="flex justify-between text-xs text-ink-muted mt-1">
          <span>1 mi</span>
          <span>5 mi</span>
          <span>10 mi</span>
          <span>15 mi</span>
          <span>20 mi</span>
          <span>25 mi</span>
        </div>
      </div>}

      {/* Listing type */}
      <div>
        <label className={labelCls}>Looking to</label>
        <div className="flex gap-1.5 flex-wrap">
          {LISTING_TYPES.map(lt => (
            <button
              key={lt.value}
              type="button"
              onClick={() => {
                setListingTypes(prev => {
                  if (prev.includes(lt.value)) { if (prev.length === 1) return prev; return prev.filter(v => v !== lt.value) }
                  return [...prev, lt.value]
                })
              }}
              className={`flex-1 py-2 text-xs rounded-lg border transition-all ${
                listingTypes.includes(lt.value)
                  ? 'bg-amber-500 border-amber-500 text-canvas-950 font-semibold'
                  : 'bg-canvas-800 border-canvas-600 text-ink-secondary hover:border-canvas-500'
              }`}
            >
              {lt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Property type */}
      <div>
        <label className={labelCls}>Property Type</label>
        <div className="flex flex-wrap gap-1.5">
          {PROPERTY_TYPES.map(pt => (
            <button
              key={pt.value}
              type="button"
              onClick={() => togglePropertyType(pt.value)}
              className={`px-3 py-1 text-xs rounded-full border transition-all ${
                criteria.property_types.includes(pt.value)
                  ? 'bg-amber-500/10 border-amber-500/50 text-amber-400'
                  : 'bg-canvas-800 border-canvas-600 text-ink-secondary hover:border-canvas-500'
              }`}
            >
              {pt.label}
            </button>
          ))}
        </div>
      </div>

      {/* House Style */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className={labelCls}>House Style</label>
          {criteria.house_styles.length > 0 && (
            <label className="flex items-center gap-1.5 cursor-pointer select-none">
              <div
                onClick={() => setCriteria(c => ({ ...c, style_strict: !c.style_strict }))}
                className={`w-8 h-4 rounded-full transition-colors relative cursor-pointer ${criteria.style_strict ? 'bg-amber-500' : 'bg-canvas-600'}`}
              >
                <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform ${criteria.style_strict ? 'translate-x-4' : 'translate-x-0.5'}`} />
              </div>
              <span className="text-xs text-ink-muted">Strict</span>
            </label>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {HOUSE_STYLES.map(hs => (
            <button
              key={hs.value}
              type="button"
              onClick={() => toggleHouseStyle(hs.value)}
              className={`px-3 py-1 text-xs rounded-full border transition-all ${
                criteria.house_styles.includes(hs.value)
                  ? 'bg-amber-500/10 border-amber-500/50 text-amber-400'
                  : 'bg-canvas-800 border-canvas-600 text-ink-secondary hover:border-canvas-500'
              }`}
            >
              {hs.label}
            </button>
          ))}
        </div>
        {criteria.house_styles.length > 0 && (
          <p className="text-xs text-ink-muted mt-1.5">
            {criteria.style_strict
              ? 'Only showing confirmed matches — listings without a detected style will be hidden.'
              : 'Showing confirmed matches + listings where style is not mentioned in the description.'}
          </p>
        )}
      </div>

      {/* Price Range */}
      <div>
        <label className={labelCls}>Price Range</label>
        <PriceRangeSlider
          minVal={priceMin}
          maxVal={priceMax}
          onMinChange={setPriceMin}
          onMaxChange={setPriceMax}
        />
      </div>

      {/* Affordability filter — only shown when mortgage bar is enabled */}
      {mortgage.enabled && (
        <div>
          <label className={labelCls}>Max Monthly Payment</label>
          <div className="flex items-center gap-2">
            <span className="text-ink-muted text-sm">$</span>
            <input
              type="number"
              placeholder="e.g. 2500"
              value={maxMonthlyPayment}
              onChange={(e) => {
                const val = e.target.value
                setMaxMonthlyPayment(val)
                const m = parseFloat(val)
                if (m > 0) {
                  const { rate, downPct, termYears } = mortgage
                  const r = rate / 100 / 12
                  const n = termYears * 12
                  const principal = r > 0
                    ? m * (Math.pow(1 + r, n) - 1) / (r * Math.pow(1 + r, n))
                    : m * n
                  setPriceMax(Math.round(principal / (1 - downPct / 100)))
                } else {
                  setPriceMax(null)
                }
              }}
              className={inputCls}
            />
            <span className="text-ink-muted text-xs whitespace-nowrap">/mo</span>
          </div>
          {maxMonthlyPayment && priceMax && (
            <p className="text-xs text-ink-muted mt-1">
              ≈ max price ${priceMax.toLocaleString()} at {mortgage.rate}% · {mortgage.downPct}% down
            </p>
          )}
        </div>
      )}

      {/* Beds / Baths / Stories */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className={labelCls}>Beds</label>
          <BtnGroup options={BEDS_OPTIONS} value={criteria.bedrooms_min} onChange={setField('bedrooms_min')} />
        </div>
        <div>
          <label className={labelCls}>Baths</label>
          <BtnGroup options={BATHS_OPTIONS} value={criteria.bathrooms_min} onChange={setField('bathrooms_min')} />
        </div>
        <div>
          <label className={labelCls}>Stories</label>
          <BtnGroup options={STORIES_OPTIONS} value={criteria.stories_min} onChange={setField('stories_min')} />
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-3 gap-x-3 gap-y-2.5">
        {[
          { label: 'Basement', field: 'has_basement', opts: TRISTATE },
          { label: 'Garage',   field: 'has_garage',   opts: TRISTATE },
          { label: 'Pool',     field: 'has_pool',     opts: TRISTATE },
          { label: 'Fireplace',field: 'has_fireplace',opts: TRISTATE },
          { label: 'A/C',      field: 'has_ac',       opts: TRISTATE },
        ].map(({ label, field, opts }) => (
          <div key={field}>
            <label className={labelCls}>{label}</label>
            <BtnGroup options={opts} value={criteria[field]} onChange={setField(field)} />
          </div>
        ))}
      </div>

      {/* Advanced toggle */}
      <button
        type="button"
        onClick={() => setShowFilters(!showFilters)}
        className="text-xs text-amber-500 hover:text-amber-400 transition-colors"
      >
        {showFilters ? '− Hide' : '+ Show'} advanced filters
      </button>

      {showFilters && (
        <div className="space-y-4 p-4 bg-canvas-800 rounded-xl border border-canvas-600">
          <div className="grid grid-cols-2 gap-3">
            <div><label className={labelCls}>Min Sqft</label><input type="number" placeholder="Any" value={criteria.sqft_min} onChange={setNum('sqft_min')} className={inputCls} /></div>
            <div><label className={labelCls}>Max Sqft</label><input type="number" placeholder="Any" value={criteria.sqft_max} onChange={setNum('sqft_max')} className={inputCls} /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={labelCls}>Min Lot (sqft)</label><input type="number" placeholder="Any" value={criteria.lot_sqft_min} onChange={setNum('lot_sqft_min')} className={inputCls} /></div>
            <div><label className={labelCls}>Max Lot (sqft)</label><input type="number" placeholder="Any" value={criteria.lot_sqft_max} onChange={setNum('lot_sqft_max')} className={inputCls} /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={labelCls}>Built After</label><input type="number" placeholder="Any" value={criteria.year_built_min} onChange={setNum('year_built_min')} className={inputCls} /></div>
            <div><label className={labelCls}>Max HOA ($/mo)</label><input type="number" placeholder="Any" value={criteria.hoa_max} onChange={setNum('hoa_max')} className={inputCls} /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className={labelCls}>Min School Rating</label>
              <select value={criteria.school_rating_min || ''} onChange={setNum('school_rating_min')} className="w-full bg-canvas-700 border border-canvas-600 text-ink-secondary rounded-lg py-2 px-3 text-sm focus:outline-none focus:border-amber-500 transition-colors">
                <option value="">Any</option>
                {[1,2,3,4,5,6,7,8,9,10].map(n => <option key={n} value={n}>{n}+</option>)}
              </select>
            </div>
            <div className="flex items-end pb-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="avoid_highways"
                  checked={criteria.avoid_highways || false}
                  onChange={(e) => setCriteria({ ...criteria, avoid_highways: e.target.checked })}
                  className="rounded border-canvas-600 bg-canvas-700 accent-amber-500"
                />
                <label htmlFor="avoid_highways" className="text-xs text-ink-muted cursor-pointer">Avoid highways</label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ZIP Results */}
      {zipResults.length > 0 && (
        <div className="p-3 bg-canvas-800 rounded-lg border border-canvas-600">
          <p className="text-xs text-ink-muted mb-2">{zipResults.length} ZIP codes · click to exclude</p>
          <div className="flex flex-wrap gap-1 max-h-28 overflow-y-auto">
            {zipResults.map(z => (
              <button
                key={z.zipcode}
                type="button"
                onClick={() => toggleZipExclude(z.zipcode)}
                title={`${z.city}, ${z.state}`}
                className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                  criteria.excluded_zips.includes(z.zipcode)
                    ? 'bg-red-500/10 border-red-500/40 text-red-400 line-through'
                    : 'bg-canvas-700 border-canvas-600 text-ink-secondary hover:border-canvas-500'
                }`}
              >
                {z.zipcode}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Draw-on-map modal */}
      {showMapDraw && (
        <div className="fixed inset-0 z-[9999] flex flex-col bg-canvas-950/95 backdrop-blur-sm">
          <div className="flex items-center justify-between px-4 py-3 border-b border-canvas-700 bg-canvas-900 shrink-0">
            <div>
              <p className="text-sm font-semibold text-ink-primary">Draw Your Search Area</p>
              <p className="text-xs text-ink-muted mt-0.5">Use the toolbar (top-left) to draw a rectangle or polygon, then release to search that area</p>
            </div>
            <button
              onClick={() => setShowMapDraw(false)}
              className="p-2 rounded-lg hover:bg-canvas-800 text-ink-muted hover:text-ink-primary transition-colors"
            >
              <X size={18} />
            </button>
          </div>
          <div className="flex-1 relative">
            {mapDrawLoading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-canvas-950/70">
                <div className="flex flex-col items-center gap-3">
                  <Loader2 size={32} className="animate-spin text-amber-400" />
                  <p className="text-sm text-ink-secondary">Finding ZIP codes in your area…</p>
                </div>
              </div>
            )}
            <ListingMap listings={[]} onPolygonComplete={handlePolygonComplete} />
          </div>
        </div>
      )}

      {/* Search + Save */}
      <div className="space-y-2 pt-1">
        <button
          type="button"
          onClick={() => handleSearch(false)}
          disabled={!criteria.location && criteria.zip_codes.length === 0}
          className="w-full flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-canvas-950 font-semibold py-3 rounded-lg text-base transition-colors"
        >
          <Search size={18} /> Search
        </button>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Name this search..."
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            className={`flex-1 ${inputCls}`}
          />
          <button
            type="button"
            onClick={() => handleSearch(true)}
            disabled={!criteria.location || !saveName}
            className="px-4 py-2 bg-canvas-800 border border-canvas-600 hover:border-amber-500 hover:text-amber-400 text-ink-secondary disabled:opacity-50 text-sm rounded-lg transition-all whitespace-nowrap"
          >
            Save & Search
          </button>
        </div>
      </div>
    </div>
  )
}
