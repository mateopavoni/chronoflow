import type { EventStatus, RunStatus } from '../../types/api'
import { cx } from '../../lib/utils'

type AnyStatus = RunStatus | EventStatus

// dot color + text color per status — borders stay neutral (industrial chip).
const DOT: Record<AnyStatus, string> = {
  pending: 'bg-on-surface-variant',
  running: 'bg-status-running',
  completed: 'bg-status-success',
  failed: 'bg-status-error',
  skipped: 'bg-on-surface-variant',
}

const TEXT: Record<AnyStatus, string> = {
  pending: 'text-on-surface-variant',
  running: 'text-status-running',
  completed: 'text-status-success',
  failed: 'text-status-error',
  skipped: 'text-on-surface-variant',
}

interface StatusBadgeProps {
  status: AnyStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 border border-outline-variant bg-surface-container px-2 py-0.5 font-mono text-label-xs uppercase tracking-wide',
        TEXT[status],
      )}
    >
      <span className={cx('h-1.5 w-1.5 shrink-0', DOT[status], status === 'running' && 'animate-pulse')} />
      {status}
    </span>
  )
}
