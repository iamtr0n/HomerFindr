import { cn } from '../../lib/utils'

const variants = {
  default: 'bg-brand-600 text-white',
  secondary: 'bg-slate-100 text-slate-800',
  success: 'bg-green-100 text-green-700',
  warning: 'bg-amber-100 text-amber-700',
  destructive: 'bg-red-100 text-red-700',
  outline: 'border border-slate-200 text-slate-700',
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
