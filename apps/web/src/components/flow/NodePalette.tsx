import { Plus } from 'lucide-react'
import type { NodeType } from '../../types/api'
import { NODE_META } from './nodeMeta'

const PALETTE_ITEMS: { type: NodeType; label: string; description: string }[] = [
  { type: 'start', label: 'Start', description: 'Entry point (exactly one)' },
  { type: 'transform', label: 'Transform', description: 'Map JSONPath fields' },
  { type: 'http', label: 'HTTP', description: 'Async HTTP request' },
  { type: 'delay', label: 'Delay', description: 'asyncio.sleep' },
  { type: 'branch', label: 'Branch', description: 'Conditional routing' },
  { type: 'end', label: 'End', description: 'Terminal node' },
]

interface NodePaletteProps {
  onAdd: (type: NodeType) => void
}

/** Sidebar palette of node types. Clicking adds the node to the canvas. */
export function NodePalette({ onAdd }: NodePaletteProps) {
  return (
    <aside
      className="flex w-56 shrink-0 flex-col overflow-y-auto border-r border-outline-variant bg-surface-container-low"
      aria-label="Node palette"
    >
      <div className="border-b border-outline-variant px-container-margin py-cell-padding-y">
        <h2 className="font-mono text-label-xs uppercase tracking-wider text-on-surface-variant">// Nodes</h2>
      </div>
      <ul className="flex flex-col" role="list">
        {PALETTE_ITEMS.map((item) => {
          const Icon = NODE_META[item.type].icon
          return (
            <li key={item.type}>
              <button
                onClick={() => onAdd(item.type)}
                className="group flex w-full items-center gap-3 border-b border-outline-variant px-container-margin py-2 text-left transition-colors hover:bg-surface-container-high"
                aria-label={`Add ${item.label} node`}
              >
                <Icon size={16} className="shrink-0 text-on-surface-variant" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-label-xs uppercase tracking-wide text-on-surface">{item.label}</div>
                  <div className="truncate font-mono text-[10px] text-on-surface-variant">{item.description}</div>
                </div>
                <Plus
                  size={14}
                  className="shrink-0 text-on-surface-variant opacity-0 transition-opacity group-hover:opacity-100"
                  aria-hidden="true"
                />
              </button>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
