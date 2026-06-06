import type { ExecutionEventOut } from '../../types/api'
import { formatDuration } from '../../lib/utils'
import { JsonViewer } from './JsonViewer'
import { StatusBadge } from './StatusBadge'

interface PayloadInspectorProps {
  event: ExecutionEventOut | null
  nodeId?: string
}

/**
 * Shows the input_snapshot, output, error and metadata of the ExecutionEvent
 * for the selected node at the current scrubber position.
 */
export function PayloadInspector({ event, nodeId }: PayloadInspectorProps) {
  if (!event) {
    return (
      <div className="p-4 text-center font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">
        {nodeId ? `No event for "${nodeId}" at this point` : 'Select a node to inspect its payload'}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">Node</p>
          <p className="font-mono text-code-sm font-semibold text-on-surface">{event.node_id}</p>
        </div>
        <StatusBadge status={event.status} />
      </div>

      {/* Timing */}
      <div className="grid grid-cols-2 gap-px border border-outline-variant bg-outline-variant">
        <div className="bg-surface px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-wide text-on-surface-variant">Sequence</span>
          <p className="font-mono text-code-sm text-on-surface">{event.sequence}</p>
        </div>
        <div className="bg-surface px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-wide text-on-surface-variant">Duration</span>
          <p className="font-mono text-code-sm text-on-surface">{formatDuration(event.duration_ms)}</p>
        </div>
      </div>

      {/* Error */}
      {event.error && (
        <div className="border border-status-error bg-status-error/10 p-3">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-status-error">Error</p>
          <p className="font-mono text-label-xs text-on-surface">{event.error}</p>
        </div>
      )}

      {/* Payloads */}
      <JsonViewer data={event.input_snapshot} label="Input snapshot" />
      <JsonViewer data={event.output} label="Output" />
    </div>
  )
}
