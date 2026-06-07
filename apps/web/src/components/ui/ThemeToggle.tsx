import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../../lib/theme'

/**
 * Light/dark theme switch. Square, monochrome, console-style.
 */
export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Light mode' : 'Dark mode'}
      className="flex h-6 w-6 items-center justify-center border border-outline-variant text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
    >
      {isDark ? <Sun size={14} /> : <Moon size={14} />}
    </button>
  )
}
