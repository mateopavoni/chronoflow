import { Link } from 'react-router-dom'
import { Workflow, ArrowRight } from 'lucide-react'

/**
 * Catch-all route ("*"). Reached for any unknown path.
 */
export function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-container-margin text-center text-on-surface">
      <Workflow size={20} className="text-on-surface-variant" aria-hidden="true" />
      <p className="font-mono text-label-xs uppercase tracking-widest text-on-surface-variant">
        404 // Not found
      </p>
      <h1 className="text-display-lg">This page doesn't exist.</h1>
      <p className="max-w-md text-body-sm text-on-surface-variant">
        The link is broken or the page moved. Head back to the landing to keep exploring
        ChronoFlow.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-code-sm font-bold uppercase tracking-wide text-on-primary transition-opacity hover:opacity-90"
      >
        Back to landing
        <ArrowRight size={14} aria-hidden="true" />
      </Link>
    </div>
  )
}
