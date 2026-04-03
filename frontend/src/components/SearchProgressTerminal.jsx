import { useEffect, useRef } from 'react'

export default function SearchProgressTerminal({ progress, searchLog, foundCount }) {
  const logRef = useRef(null)

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [searchLog])

  if (!progress && (!searchLog || searchLog.length === 0)) return null

  const pct = progress ? Math.round((progress.current / progress.total) * 100) : 100

  return (
    <div className="bg-canvas-950 border border-canvas-700 rounded-xl p-6 font-mono">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-match-strong animate-pulse" />
          <span className="text-match-strong text-xs font-medium tracking-widest uppercase">Live Search</span>
        </div>
        <span className="text-amber-400 font-mono text-sm font-medium">
          {foundCount} found so far
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-2">
        <div className="w-full bg-canvas-800 rounded-full h-2 overflow-hidden">
          <div
            className="h-2 bg-amber-500 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between mt-1.5">
          <span className="text-ink-muted text-xs">
            {progress ? `ZIP ${progress.current} / ${progress.total}` : 'Complete'}
          </span>
          <span className="text-ink-muted text-xs">{pct}%</span>
        </div>
      </div>

      {/* Log feed */}
      <div
        ref={logRef}
        className="mt-4 space-y-1 max-h-40 overflow-y-auto scrollbar-none"
      >
        {searchLog.map((entry, i) => (
          <div
            key={i}
            className="terminal-line flex items-center gap-2 text-sm"
          >
            {entry.status === 'done' ? (
              <>
                <span className="text-match-strong shrink-0">✓</span>
                <span className="text-ink-muted">{entry.zip}</span>
                {entry.count != null && (
                  <span className="text-ink-muted ml-auto">{entry.count} results</span>
                )}
              </>
            ) : (
              <>
                <span className="text-amber-400 shrink-0">›</span>
                <span className="text-ink-secondary">
                  Searching {entry.zip}{entry.location ? ` (${entry.location})` : ''} ...
                </span>
                <span className="terminal-cursor text-amber-400" />
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
