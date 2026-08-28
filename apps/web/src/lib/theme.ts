import { useSyncExternalStore } from 'react'
import { flushSync } from 'react-dom'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'chronoflow-theme'

// fixed list, add more keyframes in index.css + append here if wanted
const TRANSITIONS = ['circle', 'diagonal', 'horizontal', 'vertical'] as const

function getInitialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

// Single source of truth shared by every useTheme() caller, so the animation
// and DOM class only ever run once per change (React state alone can't do
// this across components without a context provider).
let theme: Theme = getInitialTheme()
applyTheme(theme)
const listeners = new Set<() => void>()

function commitTheme(next: Theme, persist: boolean, origin?: { x: number; y: number }) {
  const run = () => {
    theme = next
    applyTheme(next)
    if (persist) localStorage.setItem(STORAGE_KEY, next)
    listeners.forEach((l) => l())
  }

  if (origin) {
    document.documentElement.style.setProperty('--theme-x', `${origin.x}px`)
    document.documentElement.style.setProperty('--theme-y', `${origin.y}px`)
  }

  if (!document.startViewTransition) {
    run()
    return
  }
  document.documentElement.dataset.themeTransition =
    TRANSITIONS[Math.floor(Math.random() * TRANSITIONS.length)]
  document.startViewTransition(() => flushSync(run))
}

// Live OS theme changes (e.g. flipping dark mode in system settings while
// the app is open) animate too, unless the user already made an explicit choice.
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  if (localStorage.getItem(STORAGE_KEY)) return
  commitTheme(e.matches ? 'dark' : 'light', false)
})

/** Theme hook: shared across every caller, animates changes via the View Transitions API. */
export function useTheme() {
  const current = useSyncExternalStore(
    (onStoreChange) => {
      listeners.add(onStoreChange)
      return () => listeners.delete(onStoreChange)
    },
    () => theme,
  )

  const setTheme = (next: Theme) => commitTheme(next, true)
  const toggle = (origin?: { x: number; y: number }) =>
    commitTheme(current === 'dark' ? 'light' : 'dark', true, origin)

  return { theme: current, setTheme, toggle }
}
