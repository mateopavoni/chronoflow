/** @type {import('tailwindcss').Config} */

// Conductor OS design system — Swiss Minimalist / industrial console.
// Colors are driven by CSS variables (see src/index.css) so a single `.dark`
// class on <html> flips the whole theme. The `rgb(var(--x) / <alpha-value>)`
// pattern keeps Tailwind opacity utilities (bg-surface/50) working.
const token = (name) => `rgb(var(${name}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    // Sharp shapes by default — radius is the exception, not the rule.
    borderRadius: {
      none: '0',
      DEFAULT: '0',
      sm: '2px',
      md: '0',
      lg: '0',
      xl: '0',
      full: '9999px',
    },
    extend: {
      colors: {
        background: token('--background'),
        surface: token('--surface'),
        'surface-dim': token('--surface-dim'),
        'surface-container-lowest': token('--surface-container-lowest'),
        'surface-container-low': token('--surface-container-low'),
        'surface-container': token('--surface-container'),
        'surface-container-high': token('--surface-container-high'),
        'surface-container-highest': token('--surface-container-highest'),
        'on-surface': token('--on-surface'),
        'on-surface-variant': token('--on-surface-variant'),
        outline: token('--outline'),
        'outline-variant': token('--outline-variant'),
        primary: token('--primary'),
        'on-primary': token('--on-primary'),
        'primary-container': token('--primary-container'),
        'on-primary-container': token('--on-primary-container'),
        secondary: token('--secondary'),
        error: token('--error'),
        // Status colors — reserved for system feedback (used sparingly).
        'status-success': token('--status-success'),
        'status-warning': token('--status-warning'),
        'status-error': token('--status-error'),
        'status-running': token('--status-running'),
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        'display-lg': ['32px', { lineHeight: '1.2', letterSpacing: '-0.02em', fontWeight: '600' }],
        'headline-md': ['20px', { lineHeight: '1.4', letterSpacing: '-0.02em', fontWeight: '600' }],
        'body-sm': ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        'code-sm': ['13px', { lineHeight: '1.6', fontWeight: '400' }],
        'label-xs': ['11px', { lineHeight: '1', fontWeight: '500' }],
      },
      spacing: {
        unit: '4px',
        gutter: '1px',
        'cell-padding-x': '12px',
        'cell-padding-y': '8px',
        'container-margin': '16px',
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
