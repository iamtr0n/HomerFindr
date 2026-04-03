/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        canvas: {
          950: 'var(--canvas-950)',
          900: 'var(--canvas-900)',
          850: 'var(--canvas-850)',
          800: 'var(--canvas-800)',
          700: 'var(--canvas-700)',
          600: 'var(--canvas-600)',
          500: 'var(--canvas-500)',
        },
        ink: {
          primary: 'var(--ink-primary)',
          secondary: 'var(--ink-secondary)',
          muted: 'var(--ink-muted)',
        },
        match: {
          perfect: 'var(--match-perfect)',
          strong: 'var(--match-strong)',
          good: 'var(--match-good)',
          warn: 'var(--match-warn)',
        },
      },
      fontFamily: {
        sans:  ['DM Sans', 'system-ui', 'sans-serif'],
        serif: ['DM Serif Display', 'Georgia', 'serif'],
        mono:  ['DM Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'card':         '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)',
        'card-hover':   '0 8px 24px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.4)',
        'glow-amber':   '0 0 20px rgba(245,166,35,0.25)',
        'glow-match':   '0 0 16px rgba(52,211,153,0.2)',
      },
      animation: {
        'blink': 'blink 1s step-end infinite',
        'card-reveal': 'cardReveal 300ms cubic-bezier(0.34,1.56,0.64,1) forwards',
        'slide-in': 'slideIn 200ms ease-out',
      },
      keyframes: {
        blink: { '50%': { opacity: '0' } },
        cardReveal: {
          from: { opacity: '0', transform: 'translateY(12px) scale(0.97)' },
          to:   { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        slideIn: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
