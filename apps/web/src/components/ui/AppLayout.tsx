import { Outlet, Link } from 'react-router-dom'
import { Workflow } from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'

/**
 * Shared shell for top-level pages (Workflows list).
 * Editor and Debugger are full-screen and have their own headers.
 */
export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* TopAppBar */}
      <header className="flex h-10 shrink-0 items-center justify-between border-b border-outline-variant bg-surface px-container-margin">
        <Link to="/" className="flex items-center gap-2 text-on-surface transition-colors hover:text-on-surface-variant">
          <Workflow size={16} className="text-on-surface-variant" aria-hidden="true" />
          <span className="font-mono text-code-sm font-bold uppercase tracking-wider">ChronoFlow</span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="hidden font-mono text-label-xs uppercase tracking-wide text-on-surface-variant sm:inline">
            DAG Engine // Time-Travel Debugging
          </span>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}
