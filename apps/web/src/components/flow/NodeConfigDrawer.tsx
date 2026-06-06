import { useState } from 'react'
import { X } from 'lucide-react'
import type { GraphNode, NodeType, TransformConfig, HttpConfig, DelayConfig, BranchConfig } from '../../types/api'

// Shared control styles (Conductor OS — sharp, 1px border, focus → primary).
const INPUT =
  'w-full border border-outline-variant bg-surface px-3 py-1.5 text-body-sm text-on-surface placeholder:text-on-surface-variant focus:border-primary focus:outline-none'
const INPUT_MONO = INPUT + ' font-mono text-code-sm'

interface NodeConfigDrawerProps {
  node: GraphNode
  onUpdate: (node: GraphNode) => void
  onClose: () => void
}

/** Slide-in drawer for editing node label and type-specific config. */
export function NodeConfigDrawer({ node, onUpdate, onClose }: NodeConfigDrawerProps) {
  const [label, setLabel] = useState(node.data.label)
  const [config, setConfig] = useState<Record<string, unknown>>(node.data.config ?? {})

  function save() {
    onUpdate({ ...node, data: { ...node.data, label, config } })
    onClose()
  }

  function updateConfig(patch: Record<string, unknown>) {
    setConfig((prev) => ({ ...prev, ...patch }))
  }

  return (
    <aside
      className="flex w-80 shrink-0 flex-col border-l border-outline-variant bg-surface"
      aria-label="Node configuration"
    >
      <div className="flex items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-4 py-3">
        <h2 className="font-mono text-code-sm font-bold uppercase tracking-wide text-on-surface">
          {node.type} // Config
        </h2>
        <button
          onClick={onClose}
          className="flex h-6 w-6 items-center justify-center text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
          aria-label="Close drawer"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
        <div>
          <FieldLabel htmlFor="node-label">Label</FieldLabel>
          <input id="node-label" type="text" value={label} onChange={(e) => setLabel(e.target.value)} className={INPUT} />
        </div>

        <ConfigFields type={node.type} config={config} onChange={updateConfig} />
      </div>

      <div className="flex gap-2 border-t border-outline-variant p-4">
        <button
          onClick={save}
          className="flex-1 border border-primary bg-primary py-2 font-mono text-label-xs font-bold uppercase tracking-wide text-on-primary transition-colors hover:bg-transparent hover:text-on-surface"
        >
          Apply
        </button>
        <button
          onClick={onClose}
          className="border border-outline-variant px-4 py-2 font-mono text-label-xs uppercase tracking-wide text-on-surface-variant transition-colors hover:border-primary hover:text-on-surface"
        >
          Cancel
        </button>
      </div>
    </aside>
  )
}

// ─── Per-type config fields ────────────────────────────────────────────────────

interface ConfigFieldsProps {
  type: NodeType
  config: Record<string, unknown>
  onChange: (patch: Record<string, unknown>) => void
}

function ConfigFields({ type, config, onChange }: ConfigFieldsProps) {
  switch (type) {
    case 'transform':
      return <TransformFields config={config as Partial<TransformConfig>} onChange={onChange} />
    case 'http':
      return <HttpFields config={config as Partial<HttpConfig>} onChange={onChange} />
    case 'delay':
      return <DelayFields config={config as Partial<DelayConfig>} onChange={onChange} />
    case 'branch':
      return <BranchFields config={config as Partial<BranchConfig>} onChange={onChange} />
    default:
      return (
        <p className="font-mono text-label-xs text-on-surface-variant">
          No configurable options for this node type.
        </p>
      )
  }
}

function FieldLabel({ htmlFor, children }: { htmlFor: string; children: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">
      {children}
    </label>
  )
}

function FieldHint({ children }: { children: React.ReactNode }) {
  return <p className="mt-1 font-mono text-[10px] text-on-surface-variant">{children}</p>
}

function TransformFields({ config, onChange }: { config: Partial<TransformConfig>; onChange: (p: Record<string, unknown>) => void }) {
  const mappings = config.mappings ?? {}
  const [rawJson, setRawJson] = useState(JSON.stringify(mappings, null, 2))
  const [jsonError, setJsonError] = useState<string | null>(null)

  function handleChange(val: string) {
    setRawJson(val)
    try {
      const parsed = JSON.parse(val) as Record<string, string>
      setJsonError(null)
      onChange({ mappings: parsed })
    } catch {
      setJsonError('Invalid JSON')
    }
  }

  return (
    <div>
      <FieldLabel htmlFor="transform-mappings">Mappings (JSON)</FieldLabel>
      <textarea
        id="transform-mappings"
        value={rawJson}
        onChange={(e) => handleChange(e.target.value)}
        rows={6}
        className={INPUT_MONO + ' resize-y'}
        placeholder={'{\n  "outputKey": "$.nodeId.field"\n}'}
      />
      {jsonError && <p className="mt-1 font-mono text-[10px] text-status-error">{jsonError}</p>}
      <FieldHint>Keys → JSONPath expressions from context</FieldHint>
    </div>
  )
}

function HttpFields({ config, onChange }: { config: Partial<HttpConfig>; onChange: (p: Record<string, unknown>) => void }) {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <FieldLabel htmlFor="http-method">Method</FieldLabel>
        <select
          id="http-method"
          value={config.method ?? 'GET'}
          onChange={(e) => onChange({ method: e.target.value })}
          className={INPUT}
        >
          {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>
      <div>
        <FieldLabel htmlFor="http-url">URL</FieldLabel>
        <input
          id="http-url"
          type="text"
          value={config.url ?? ''}
          onChange={(e) => onChange({ url: e.target.value })}
          className={INPUT_MONO}
          placeholder="https://api.example.com/..."
        />
        <FieldHint>Supports templates: {'${$.nodeId.field}'}</FieldHint>
      </div>
    </div>
  )
}

function DelayFields({ config, onChange }: { config: Partial<DelayConfig>; onChange: (p: Record<string, unknown>) => void }) {
  return (
    <div>
      <FieldLabel htmlFor="delay-seconds">Seconds</FieldLabel>
      <input
        id="delay-seconds"
        type="number"
        min={0}
        step={0.5}
        value={config.seconds ?? 1}
        onChange={(e) => onChange({ seconds: parseFloat(e.target.value) })}
        className={INPUT}
      />
    </div>
  )
}

function BranchFields({ config, onChange }: { config: Partial<BranchConfig>; onChange: (p: Record<string, unknown>) => void }) {
  return (
    <div>
      <FieldLabel htmlFor="branch-condition">Condition</FieldLabel>
      <input
        id="branch-condition"
        type="text"
        value={config.condition ?? ''}
        onChange={(e) => onChange({ condition: e.target.value })}
        className={INPUT_MONO}
        placeholder="$.nodeId.value > 10"
      />
      <FieldHint>JSONPath expression + comparison operator</FieldHint>
    </div>
  )
}
