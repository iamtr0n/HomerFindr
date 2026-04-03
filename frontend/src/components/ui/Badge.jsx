import { cn } from '../../lib/utils'

const variants = {
  default:     'bg-amber-500 text-canvas-950',
  secondary:   'bg-canvas-700 text-ink-secondary',
  success:     'bg-match-strong/10 text-match-strong border border-match-strong/30',
  warning:     'bg-match-warn/10 text-match-warn border border-match-warn/30',
  destructive: 'bg-red-400/10 text-red-400 border border-red-400/30',
  outline:     'border border-canvas-600 text-ink-muted',
}

export function Badge({ variant = 'default', className, ...props }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variants[variant],
        className
      )}
      {...props}
    />
  )
}
