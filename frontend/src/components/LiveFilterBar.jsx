import { useState } from 'react'
import { SlidersHorizontal, X } from 'lucide-react'
import PriceRangeSlider from './PriceRangeSlider'

const LISTING_TYPES = [
  { value: 'sale', label: 'For Sale' },
  { value: 'pending', label: 'Pending' },
  { value: 'coming_soon', label: 'Coming Soon' },
  { value: 'sold', label: 'Sold' },
  { value: 'rent', label: 'Rent' },
]
const BED_OPTIONS = [
  { value: null, label: 'Any' },
  { value: 1, label: '1+' },
  { value: 2, label: '2+' },
  { value: 3, label: '3+' },
  { value: 4, label: '4+' },
]
const BATH_OPTIONS = [
  { value: null, label: 'Any' },
  { value: 1, label: '1+' },
  { value: 2, label: '2+' },
  { value: 3, label: '3+' },
]

export default function LiveFilterBar({ totalCount, filteredCount, filters, onChange, availableZips = [] }) {
  // filters shape: { priceMin, priceMax, bedsMin, bathsMin, listingTypes, propertyTypes, selectedZips }
  const [expanded, setExpanded] = useState(false)

  const hasActiveFilters = filters.priceMin || filters.priceMax ||
    filters.bedsMin || filters.bathsMin ||
    (filters.listingTypes && filters.listingTypes.length > 0) ||
    (filters.selectedZips && filters.selectedZips.length > 0)

  const reset = () => onChange({
    priceMin: null, priceMax: null,
    bedsMin: null, bathsMin: null,
    listingTypes: [], propertyTypes: [], selectedZips: [],
  })

  const toggleType = (val) => {
    const types = filters.listingTypes || []
    const next = types.includes(val) ? types.filter(t => t !== val) : [...types, val]
    onChange({ ...filters, listingTypes: next })
  }

  const pill = (active) =>
    `px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors cursor-pointer ` +
    (active
      ? 'bg-amber-500/20 border-amber-500 text-amber-400'
      : 'bg-canvas-800 border-canvas-600 text-ink-secondary hover:border-canvas-500 hover:text-ink-primary')

  return (
    <div className="bg-canvas-900 border border-canvas-700 rounded-xl mb-5 overflow-hidden">
      {/* Header row */}
      <div className="flex items-center justify-between px-4 py-2.5 gap-3">
        <div className="flex items-center gap-2">
          <SlidersHorizontal size={14} className="text-ink-muted" />
          <span className="text-xs text-ink-secondary font-medium">
            Showing <span className="text-ink-primary font-semibold">{filteredCount}</span>
            {filteredCount !== totalCount && (
              <span className="text-ink-muted"> of {totalCount}</span>
            )} properties
          </span>
          {hasActiveFilters && (
            <button onClick={reset} className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 ml-1">
              <X size={11} />Clear
            </button>
          )}
        </div>
        <button
          onClick={() => setExpanded(p => !p)}
          className={`text-xs px-3 py-1 rounded-lg border transition-colors ${
            expanded
              ? 'bg-amber-500/10 border-amber-500/40 text-amber-400'
              : 'bg-canvas-800 border-canvas-600 text-ink-secondary hover:border-canvas-500'
          }`}
        >
          {expanded ? 'Less filters' : 'Refine'}
        </button>
      </div>

      {/* Expanded filters */}
      {expanded && (
        <div className="border-t border-canvas-700 px-4 py-3 space-y-3">
          {/* Listing type pills */}
          <div className="flex flex-wrap gap-1.5">
            {LISTING_TYPES.map(t => (
              <button
                key={t.value}
                onClick={() => toggleType(t.value)}
                className={pill((filters.listingTypes || []).includes(t.value))}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Price range */}
          <div>
            <p className="text-xs text-ink-muted mb-1.5 uppercase tracking-widest font-medium">Price</p>
            <PriceRangeSlider
              minVal={filters.priceMin}
              maxVal={filters.priceMax}
              onMinChange={(v) => onChange({ ...filters, priceMin: v })}
              onMaxChange={(v) => onChange({ ...filters, priceMax: v })}
            />
          </div>

          {/* Beds / Baths */}
          <div className="flex gap-6">
            <div>
              <p className="text-xs text-ink-muted mb-1.5 uppercase tracking-widest font-medium">Beds</p>
              <div className="flex gap-1">
                {BED_OPTIONS.map(o => (
                  <button key={String(o.value)} onClick={() => onChange({ ...filters, bedsMin: o.value })} className={pill(filters.bedsMin === o.value)}>
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-ink-muted mb-1.5 uppercase tracking-widest font-medium">Baths</p>
              <div className="flex gap-1">
                {BATH_OPTIONS.map(o => (
                  <button key={String(o.value)} onClick={() => onChange({ ...filters, bathsMin: o.value })} className={pill(filters.bathsMin === o.value)}>
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* ZIP / Area filter */}
          {availableZips && availableZips.length > 1 && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs text-ink-muted uppercase tracking-widest font-medium">Areas</p>
                {(filters.selectedZips || []).length > 0 && (
                  <button
                    onClick={() => onChange({ ...filters, selectedZips: [] })}
                    className="text-xs text-amber-400 hover:text-amber-300"
                  >
                    Show all
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto scrollbar-none">
                {availableZips.map(({ zip, city, count }) => {
                  const active = !(filters.selectedZips?.length > 0) || filters.selectedZips.includes(zip)
                  const toggle = () => {
                    const current = filters.selectedZips || []
                    let next
                    if (current.length === 0) {
                      next = [zip]
                    } else if (current.includes(zip)) {
                      next = current.filter(z => z !== zip)
                      if (next.length === availableZips.length) next = []
                    } else {
                      next = [...current, zip]
                      if (next.length === availableZips.length) next = []
                    }
                    onChange({ ...filters, selectedZips: next })
                  }
                  return (
                    <button
                      key={zip}
                      onClick={toggle}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                        active
                          ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                          : 'bg-canvas-800 border-canvas-600 text-ink-muted opacity-50 hover:opacity-80'
                      }`}
                    >
                      {city ? `${city}` : zip} <span className="opacity-60">({count})</span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
