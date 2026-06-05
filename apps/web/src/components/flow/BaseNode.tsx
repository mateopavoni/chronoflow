import { Handle, Position } from '@xyflow/react'
import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cx } from '../../lib/utils'
import { HANDLE_CLASS } from './nodeMeta'

interface BaseNodeProps {
  label: string
  icon: LucideIcon
  tag: string
  /** Optional 2px top accent bar color (Tailwind bg-* class). Defaults to neutral. */
  accentClass?: string
  children?: ReactNode
  hasInput?: boolean
  hasOutput?: boolean
  selected?: boolean
}

/**
 * Shared shell for all editor node types — Conductor OS console card:
 * 1px border, sharp corners, mono header with type tag, no shadow.
 */
export function BaseNode({
  label,
  icon: Icon,
  tag,
  accentClass = 'bg-outline-variant',
  children,
  hasInput = true,
  hasOutput = true,
  selected = false,
}: BaseNodeProps) {
  return (
    <div
      className="relative min-w-[180px] max-w-[240px] border border-outline-variant bg-surface text-on-surface"
      role="group"
      aria-label={label}
    >
      {selected && (
        <div className="pointer-events-none absolute inset-[-3px] border border-primary" aria-hidden="true" />
      )}

      {hasInput && <Handle type="target" position={Position.Top} className={HANDLE_CLASS} />}

      {/* Top accent bar */}
      <div className={cx('h-[2px] w-full', accentClass)} />

      {/* Header */}
      <div className="flex items-center gap-2 border-b border-outline-variant bg-surface-container-lowest px-2 py-1.5">
        <Icon size={14} className="shrink-0 text-on-surface-variant" aria-hidden="true" />
        <span className="flex-1 truncate font-mono text-label-xs font-medium uppercase tracking-wide text-on-surface">
          {label}
        </span>
        <span className="shrink-0 font-mono text-[10px] text-on-surface-variant">{tag}</span>
      </div>

      {/* Body */}
      {children && (
        <div className="px-2 py-1.5 font-mono text-label-xs text-on-surface-variant">{children}</div>
      )}

      {hasOutput && <Handle type="source" position={Position.Bottom} className={HANDLE_CLASS} />}
    </div>
  )
}
