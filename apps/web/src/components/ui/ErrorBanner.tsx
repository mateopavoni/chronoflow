import { AlertTriangle } from 'lucide-react'

interface ErrorBannerProps {
  message: string
  onRetry?: () => void
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 border border-status-error bg-status-error/10 p-4"
    >
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-status-error" aria-hidden="true" />
      <div className="flex-1">
        <p className="font-mono text-label-xs uppercase tracking-wide text-status-error">Something went wrong</p>
        <p className="mt-1 whitespace-pre-line text-body-sm text-on-surface">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 border border-outline-variant px-2 py-1 font-mono text-label-xs uppercase tracking-wide text-on-surface-variant transition-colors hover:border-primary hover:text-on-surface"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  )
}
