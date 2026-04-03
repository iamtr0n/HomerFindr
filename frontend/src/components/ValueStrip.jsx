const PILLS = [
  { text: 'No ads or sponsored listings' },
  { text: 'No fake Zestimate' },
  { text: 'Real MLS data via Realtor.com' },
  { text: 'Zero upsells. Ever.' },
  { text: 'Runs locally — your data stays yours' },
  { text: 'Match scoring based on your criteria' },
]

export default function ValueStrip() {
  return (
    <div className="bg-canvas-900 border-b border-canvas-700 px-6 py-2.5 overflow-x-auto scrollbar-none">
      <div className="flex gap-3 w-max">
        {PILLS.map((pill, i) => (
          <div key={i} className="flex items-center gap-1.5 bg-canvas-800 border border-canvas-700 rounded-full px-3.5 py-1 whitespace-nowrap">
            <span className="text-match-strong text-xs font-medium">✓</span>
            <span className="text-ink-muted text-xs">{pill.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
