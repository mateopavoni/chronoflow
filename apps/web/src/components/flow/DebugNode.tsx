import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { EventStatus, NodeType } from '../../types/api'
import { cx } from '../../lib/utils'
import { HANDLE_CLASS, NODE_META } from './nodeMeta'

/**
 * Generic node for the RunDebugger canvas. The top accent bar and status line
 * are colored by execution status; type is shown by icon + tag.
 */

type Status = EventStatus | 'pending'

const STATUS_BAR: Record<Status, string> = {
  pending: 'bg-outline-variant',
  running: 'bg-status-running animate-pulse',
  completed: 'bg-status-success',
  failed: 'bg-status-error',
  skipped: 'bg-outline-variant',
}

const STATUS_TEXT: Record<Status, string> = {
  pending: 'text-on-surface-variant',
  running: 'text-status-running',
  completed: 'text-status-success',
  failed: 'text-status-error',
  skipped: 'text-on-surface-variant',
}

interface DebugNodeData {
  label: string
  nodeType: NodeType
  status: Status
  durationMs?: number | null
  [key: string]: unknown
}

export function DebugNode({ data, selected }: NodeProps) {
  const d = data as DebugNodeData
  const status: Status = d.status ?? 'pending'
  const { icon: Icon, tag } = NODE_META[d.nodeType] ?? NODE_META.transform
  const isBranch = d.nodeType === 'branch'
  const duration =
    d.durationMs != null
      ? d.durationMs < 1000
        ? `${d.durationMs}ms`
        : `${(d.durationMs / 1000).toFixed(1)}s`
      : null

  return (
    <div
      className={cx(
        'relative min-w-[170px] max-w-[220px] border bg-surface text-on-surface',
        status === 'failed' ? 'border-status-error' : 'border-outline-variant',
        status === 'skipped' && 'opacity-60',
      )}
      role="group"
      aria-label={`${d.label} — ${status}`}
    >
      {selected && (
        <div className="pointer-events-none absolute inset-[-3px] border border-primary" aria-hidden="true" />
      )}

      <Handle type="target" position={Position.Top} className={HANDLE_CLASS} />

      {/* Status bar */}
      <div className={cx('h-[2px] w-full', STATUS_BAR[status])} />

      {/* Header */}
      <div className="flex items-center gap-2 border-b border-outline-variant bg-surface-container-lowest px-2 py-1.5">
        <Icon size={14} className="shrink-0 text-on-surface-variant" aria-hidden="true" />
        <span className="flex-1 truncate font-mono text-label-xs font-medium uppercase tracking-wide text-on-surface">
          {d.label}
        </span>
        {duration && <span className="shrink-0 font-mono text-[10px] text-on-surface-variant">{duration}</span>}
      </div>

      {/* Status line */}
      <div className="flex items-center justify-between px-2 py-1.5 font-mono text-label-xs">
        <span className={cx('uppercase tracking-wide', STATUS_TEXT[status])}>{status}</span>
        <span className="text-[10px] text-on-surface-variant">{tag}</span>
      </div>

      {isBranch ? (
        <>
          <div className="flex justify-between border-t border-outline-variant px-3 py-1 font-mono text-[10px] uppercase">
            <span className="text-status-success">true</span>
            <span className="text-status-error">false</span>
          </div>
          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            style={{ left: '25%' }}
            className="!h-2.5 !w-2.5 !rounded-none !border !border-status-success !bg-surface"
          />
          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            style={{ left: '75%' }}
            className="!h-2.5 !w-2.5 !rounded-none !border !border-status-error !bg-surface"
          />
        </>
      ) : (
        <Handle type="source" position={Position.Bottom} className={HANDLE_CLASS} />
      )}
    </div>
  )
}
