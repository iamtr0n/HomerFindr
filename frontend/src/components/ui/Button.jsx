import { cn } from '../../lib/utils'

const variants = {
  default:     'bg-amber-500 text-canvas-950 hover:bg-amber-400 font-semibold',
  secondary:   'bg-canvas-800 text-ink-secondary border border-canvas-600 hover:border-canvas-500 hover:text-ink-primary',
  outline:     'border border-canvas-600 bg-transparent text-ink-secondary hover:border-amber-500 hover:text-amber-400',
  ghost:       'text-ink-secondary hover:bg-canvas-800 hover:text-ink-primary',
  destructive: 'bg-red-600 text-white hover:bg-red-500',
}

const sizes = {
  sm:   'px-3 py-1.5 text-sm',
  md:   'px-4 py-2 text-sm',
  lg:   'px-6 py-3 text-base',
  icon: 'p-2',
}

export function Button({ variant = 'default', size = 'md', className, ...props }) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  )
}
