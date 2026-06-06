import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { BranchConfig } from '../../types/api'
import { HANDLE_CLASS, NODE_META } from './nodeMeta'

/**
 * Branch node: one input on top, two outputs on bottom (true=left, false=right).
 * Uses explicit Handle IDs so edges can be labeled 'true'/'false'.
 */
export function BranchNode({ data, selected }: NodeProps) {
  const config = data?.['config'] as BranchConfig | undefined
  const condition = config?.condition ?? ''
  const label = typeof data?.['label'] === 'string' ? data['label'] : 'Branch'
  const shortCond = condition.length > 30 ? condition.slice(0, 27) + '…' : condition
  const { icon: Icon, tag } = NODE_META.branch

  return (
    <div
      className="relative min-w-[200px] max-w-[260px] border border-outline-variant bg-surface text-on-surface"
      role="group"
      aria-label={label}
    >
      {selected && (
        <div className="pointer-events-none absolute inset-[-3px] border border-primary" aria-hidden="true" />
      )}

      <Handle type="target" position={Position.Top} className={HANDLE_CLASS} />

      <div className="h-[2px] w-full bg-outline-variant" />

      {/* Header */}
      <div className="flex items-center gap-2 border-b border-outline-variant bg-surface-container-lowest px-2 py-1.5">
        <Icon size={14} className="shrink-0 text-on-surface-variant" aria-hidden="true" />
        <span className="flex-1 truncate font-mono text-label-xs font-medium uppercase tracking-wide text-on-surface">
          {label}
        </span>
        <span className="shrink-0 font-mono text-[10px] text-on-surface-variant">{tag}</span>
      </div>

      {/* Condition */}
      <div className="px-2 py-1.5 font-mono text-label-xs text-on-surface-variant">
        {shortCond || <span className="text-on-surface-variant/60">no condition</span>}
      </div>

      {/* Two output labels */}
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
    </div>
  )
}
