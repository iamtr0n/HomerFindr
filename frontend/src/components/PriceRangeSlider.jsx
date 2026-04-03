// Stepped price array — dense at lower values for natural zoom-in precision
const STEPS = [
  0,
  50000, 75000, 100000, 125000, 150000, 175000, 200000, 225000, 250000,
  275000, 300000, 325000, 350000, 375000, 400000, 425000, 450000, 475000, 500000,
  550000, 600000, 650000, 700000, 750000, 800000, 850000, 900000, 950000, 1000000,
  1100000, 1200000, 1300000, 1500000, 1750000, 2000000, 2500000, 3000000, 4000000, 5000000,
]
const N = STEPS.length - 1

const priceToIdx = (price) => {
  if (!price || price <= 0) return 0
  for (let i = STEPS.length - 1; i >= 0; i--) {
    if (STEPS[i] <= price) return i
  }
  return 0
}

const fmt = (v) => {
  if (!v) return 'Any'
  if (v >= 1000000) {
    const m = v / 1000000
    return `$${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M`
  }
  return `$${(v / 1000).toFixed(0)}k`
}

export default function PriceRangeSlider({ minVal, maxVal, onMinChange, onMaxChange }) {
  const minIdx = priceToIdx(minVal)
  const maxIdx = maxVal ? priceToIdx(maxVal) : N

  const leftPct = (minIdx / N) * 100
  const rightPct = (maxIdx / N) * 100

  const handleMin = (e) => {
    const idx = Math.min(Number(e.target.value), maxIdx - 1)
    onMinChange(idx <= 0 ? null : STEPS[idx])
  }

  const handleMax = (e) => {
    const idx = Math.max(Number(e.target.value), minIdx + 1)
    onMaxChange(idx >= N ? null : STEPS[idx])
  }

  const anyPrice = !minVal && !maxVal

  return (
    <div className="space-y-1.5">
      <div className="relative h-5 flex items-center">
        <div className="absolute w-full h-1 bg-canvas-700 rounded-full" />
        <div
          className="absolute h-1 bg-amber-500 rounded-full"
          style={{ left: `${leftPct}%`, right: `${100 - rightPct}%` }}
        />
        <input
          type="range" min={0} max={N} step={1} value={minIdx}
          onChange={handleMin}
          className="absolute w-full appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-amber-500 [&::-webkit-slider-thumb]:border-0 [&::-webkit-slider-thumb]:appearance-none z-10"
        />
        <input
          type="range" min={0} max={N} step={1} value={maxIdx}
          onChange={handleMax}
          className="absolute w-full appearance-none bg-transparent pointer-events-none [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-amber-500 [&::-webkit-slider-thumb]:border-0 [&::-webkit-slider-thumb]:appearance-none z-10"
        />
      </div>
      <div className="flex justify-between text-xs">
        <span className={minVal ? 'text-amber-400 font-medium' : 'text-ink-muted'}>{fmt(minVal)}</span>
        <span className="text-ink-muted">{anyPrice ? 'any price' : `${fmt(minVal)} – ${fmt(maxVal)}`}</span>
        <span className={maxVal ? 'text-amber-400 font-medium' : 'text-ink-muted'}>{fmt(maxVal)}</span>
      </div>
    </div>
  )
}
