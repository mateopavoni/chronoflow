import { Outlet, Link, useNavigate } from 'react-router-dom'
import { Workflow, LogOut } from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'
import { useLogout, useMe } from '../../hooks/useAuth'

/**
 * Shared shell for top-level pages (Workflows list).
 * Editor and Debugger are full-screen and have their own headers.
 */
export function AppLayout() {
  const navigate = useNavigate()
  const { data: user } = useMe()
  const logout = useLogout()

  async function handleLogout() {
    await logout.mutateAsync()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* TopAppBar */}
      <header className="flex h-10 shrink-0 items-center justify-between border-b border-outline-variant bg-surface px-container-margin">
        <Link to="/app" className="flex items-center gap-2 text-on-surface transition-colors hover:text-on-surface-variant">
          <Workflow size={16} className="text-on-surface-variant" aria-hidden="true" />
          <span className="font-mono text-code-sm font-bold uppercase tracking-wider">ChronoFlow</span>
        </Link>
        <div className="flex items-center gap-3">
          {user && (
            <span className="hidden font-mono text-label-xs lowercase tracking-wide text-on-surface-variant sm:inline">
              {user.email}
            </span>
          )}
          <ThemeToggle />
          <button
            onClick={() => void handleLogout()}
            disabled={logout.isPending}
            aria-label="Sign out"
            className="flex items-center gap-1 font-mono text-label-xs uppercase tracking-wide text-on-surface-variant transition-colors hover:text-on-surface disabled:opacity-50"
          >
            <LogOut size={14} aria-hidden="true" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}
