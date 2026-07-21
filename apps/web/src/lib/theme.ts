import { useEffect, useState } from 'react'
import { flushSync } from 'react-dom'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'chronoflow-theme'

/** Read the persisted theme, falling back to the OS preference. */
export function getInitialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

// ponytail: fixed list, add more keyframes in index.css + append here if wanted
const TRANSITIONS = ['circle', 'diagonal', 'horizontal', 'vertical'] as const

/**
 * Theme hook: keeps the `.dark` class on <html> in sync, persists the choice,
 * and exposes a toggle. The initial class is set by an inline script in
 * index.html (before paint) to avoid a flash; this hook takes over after mount.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const toggle = (origin?: { x: number; y: number }) => {
    const next = theme === 'dark' ? 'light' : 'dark'

    if (origin) {
      document.documentElement.style.setProperty('--theme-x', `${origin.x}px`)
      document.documentElement.style.setProperty('--theme-y', `${origin.y}px`)
    }

    if (!document.startViewTransition) {
      setTheme(next)
      return
    }
    document.documentElement.dataset.themeTransition =
      TRANSITIONS[Math.floor(Math.random() * TRANSITIONS.length)]
    document.startViewTransition(() => flushSync(() => setTheme(next)))
  }

  return { theme, setTheme, toggle }
}
