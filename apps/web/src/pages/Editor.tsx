import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ArrowLeft, CheckCircle2, Play, Redo2, Undo2, XCircle } from 'lucide-react'

import { useRunWorkflow, useUpdateWorkflow, useValidateWorkflow, useWorkflow } from '../hooks/useWorkflows'
import { NODE_TYPES } from '../components/flow/nodeTypes'
import { NodePalette } from '../components/flow/NodePalette'
import { NodeConfigDrawer } from '../components/flow/NodeConfigDrawer'
import { Modal } from '../components/ui/Modal'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { ThemeToggle } from '../components/ui/ThemeToggle'
import { generateId, tryParseJson } from '../lib/utils'
import { cloneWithNewIds, extractSelection, type ClipboardData } from '../lib/clipboard'
import { useTheme } from '../lib/theme'
import type { GraphEdge, GraphNode, NodeType, ValidationResult } from '../types/api'

// Branch edge colors (kept literal; React Flow inline styles can't use CSS vars).
const EDGE_TRUE = '#22c55e'
const EDGE_FALSE = '#ef4444'

// ─── Convert between our Graph types and React Flow types ─────────────────────

function toFlowNode(n: GraphNode): Node {
  return { id: n.id, type: n.type, position: n.position, data: n.data }
}

function toFlowEdge(e: GraphEdge): Edge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.data?.branch ?? null,
    label: e.data?.branch,
    data: e.data,
    animated: false,
    style:
      e.data?.branch === 'true'
        ? { stroke: EDGE_TRUE }
        : e.data?.branch === 'false'
          ? { stroke: EDGE_FALSE }
          : undefined,
  }
}

function fromFlowNode(n: Node): GraphNode {
  return { id: n.id, type: n.type as NodeType, position: n.position, data: n.data as GraphNode['data'] }
}

function fromFlowEdge(e: Edge): GraphEdge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    data:
      (e.data as GraphEdge['data']) ??
      (e.sourceHandle ? { branch: e.sourceHandle as 'true' | 'false' } : undefined),
  }
}

const DEFAULT_NODE_CONFIGS: Record<NodeType, Record<string, unknown>> = {
  start: {},
  end: {},
  transform: { mappings: {} },
  http: { method: 'GET', url: '' },
  delay: { seconds: 1 },
  branch: { condition: '' },
}

// Shared toolbar button styles
const BTN_SECONDARY =
  'border border-outline-variant px-3 py-1 font-mono text-label-xs uppercase tracking-wide text-on-surface-variant transition-colors hover:border-primary hover:text-on-surface disabled:opacity-60'
const BTN_STRONG =
  'border border-outline-variant bg-surface-container-high px-3 py-1 font-mono text-label-xs uppercase tracking-wide text-on-surface transition-colors hover:bg-surface-container-highest disabled:opacity-60'
const BTN_PRIMARY =
  'flex items-center gap-1.5 border border-primary bg-primary px-3 py-1 font-mono text-label-xs font-bold uppercase tracking-wide text-on-primary transition-colors hover:bg-transparent hover:text-on-surface disabled:opacity-60'
const BTN_ICON =
  'flex items-center justify-center border border-outline-variant px-2 py-1 text-on-surface-variant transition-colors hover:border-primary hover:text-on-surface disabled:opacity-40 disabled:hover:border-outline-variant disabled:hover:text-on-surface-variant'

/** "/workflows/:id" — Visual DAG editor. */
export function Editor() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { theme } = useTheme()

  const { data: workflow, isLoading, isError, error } = useWorkflow(id)
  const updateMutation = useUpdateWorkflow(id)
  const validateMutation = useValidateWorkflow()
  const runMutation = useRunWorkflow()

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [initialized, setInitialized] = useState(false)

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [showRunModal, setShowRunModal] = useState(false)
  const [triggerJson, setTriggerJson] = useState('{}')
  const [triggerJsonError, setTriggerJsonError] = useState<string | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [nameEdit, setNameEdit] = useState('')

  if (workflow && !initialized) {
    setNodes(workflow.graph.nodes.map(toFlowNode))
    setEdges(workflow.graph.edges.map(toFlowEdge))
    setNameEdit(workflow.name)
    setInitialized(true)
  }

  // ─── Undo/redo history + clipboard ──────────────────────────────────────────
  // Refs mirror the latest nodes/edges so the (once-bound) keyboard handler and
  // the history helpers never read a stale closure.
  const nodesRef = useRef(nodes)
  nodesRef.current = nodes
  const edgesRef = useRef(edges)
  edgesRef.current = edges

  const past = useRef<{ nodes: Node[]; edges: Edge[] }[]>([])
  const future = useRef<{ nodes: Node[]; edges: Edge[] }[]>([])
  const clipboard = useRef<ClipboardData | null>(null)
  // Force a re-render so the toolbar's undo/redo enabled state stays in sync
  // (history lives in refs, which don't trigger renders on their own).
  const [, bumpHistory] = useReducer((n: number) => n + 1, 0)

  /** Snapshot the current canvas onto the undo stack (call BEFORE a mutation). */
  const takeSnapshot = useCallback(() => {
    past.current.push({ nodes: nodesRef.current, edges: edgesRef.current })
    if (past.current.length > 50) past.current.shift()
    future.current = []
    bumpHistory()
  }, [])

  const undo = useCallback(() => {
    const prev = past.current.pop()
    if (!prev) return
    future.current.push({ nodes: nodesRef.current, edges: edgesRef.current })
    setNodes(prev.nodes)
    setEdges(prev.edges)
    setSelectedNodeId(null)
    bumpHistory()
  }, [setNodes, setEdges])

  const redo = useCallback(() => {
    const next = future.current.pop()
    if (!next) return
    past.current.push({ nodes: nodesRef.current, edges: edgesRef.current })
    setNodes(next.nodes)
    setEdges(next.edges)
    setSelectedNodeId(null)
    bumpHistory()
  }, [setNodes, setEdges])

  /** Copy the current selection to the in-memory clipboard. Returns false if empty. */
  const copySelection = useCallback(() => {
    const clip = extractSelection(nodesRef.current, edgesRef.current)
    if (clip.nodes.length === 0) return false
    clipboard.current = clip
    return true
  }, [])

  /** Delete selected nodes (+ their edges) and any selected edges. */
  const deleteSelection = useCallback(() => {
    const hasSel = nodesRef.current.some((n) => n.selected) || edgesRef.current.some((e) => e.selected)
    if (!hasSel) return
    takeSnapshot()
    const ids = new Set(nodesRef.current.filter((n) => n.selected).map((n) => n.id))
    setNodes((nds) => nds.filter((n) => !n.selected))
    setEdges((eds) => eds.filter((e) => !e.selected && !ids.has(e.source) && !ids.has(e.target)))
    setSelectedNodeId(null)
  }, [takeSnapshot, setNodes, setEdges])

  const cutSelection = useCallback(() => {
    if (!copySelection()) return
    deleteSelection()
  }, [copySelection, deleteSelection])

  const paste = useCallback(() => {
    const clip = clipboard.current
    if (!clip || clip.nodes.length === 0) return
    takeSnapshot()
    const cloned = cloneWithNewIds(clip, { genId: () => generateId().slice(0, 8) })
    setNodes((nds) => [...nds.map((n) => (n.selected ? { ...n, selected: false } : n)), ...cloned.nodes])
    setEdges((eds) => [...eds, ...cloned.edges])
  }, [takeSnapshot, setNodes, setEdges])

  // Bind keyboard shortcuts once. Ignored while typing in inputs/textareas.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      const mod = e.ctrlKey || e.metaKey
      if (mod) {
        const k = e.key.toLowerCase()
        if (k === 'z' && !e.shiftKey) {
          e.preventDefault()
          undo()
        } else if ((k === 'z' && e.shiftKey) || k === 'y') {
          e.preventDefault()
          redo()
        } else if (k === 'c') {
          if (copySelection()) e.preventDefault()
        } else if (k === 'x') {
          e.preventDefault()
          cutSelection()
        } else if (k === 'v') {
          e.preventDefault()
          paste()
        }
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault()
        deleteSelection()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [undo, redo, copySelection, cutSelection, paste, deleteSelection])

  const onConnect = useCallback(
    (connection: Connection) => {
      takeSnapshot()
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            id: `edge-${generateId()}`,
            label: connection.sourceHandle ?? undefined,
            data: connection.sourceHandle ? { branch: connection.sourceHandle as 'true' | 'false' } : undefined,
            style:
              connection.sourceHandle === 'true'
                ? { stroke: EDGE_TRUE }
                : connection.sourceHandle === 'false'
                  ? { stroke: EDGE_FALSE }
                  : undefined,
          },
          eds,
        ),
      )
    },
    [setEdges, takeSnapshot],
  )

  function addNode(type: NodeType) {
    takeSnapshot()
    const newNode: Node = {
      id: `${type}-${generateId().slice(0, 8)}`,
      type,
      position: { x: 200 + Math.random() * 200, y: 150 + Math.random() * 150 },
      data: { label: type.charAt(0).toUpperCase() + type.slice(1), config: DEFAULT_NODE_CONFIGS[type] },
    }
    setNodes((nds) => [...nds, newNode])
  }

  function updateNode(updated: GraphNode) {
    takeSnapshot()
    setNodes((nds) => nds.map((n) => (n.id === updated.id ? { ...n, data: updated.data } : n)))
    setSelectedNodeId(null)
  }

  /** Persist the current canvas. Throws on failure so callers can react. */
  async function persistGraph() {
    if (!workflow) return
    await updateMutation.mutateAsync({
      name: nameEdit,
      description: workflow.description,
      graph: { nodes: nodes.map(fromFlowNode), edges: edges.map(fromFlowEdge) },
    })
  }

  async function handleSave() {
    try {
      await persistGraph()
    } catch {
      // Surfaced via updateMutation.isError in the toolbar; swallow the rejection.
    }
  }

  async function handleValidate() {
    try {
      const result = await validateMutation.mutateAsync(id)
      setValidationResult(result)
    } catch {
      // Validate rarely fails (404); ignore to avoid an unhandled rejection.
    }
  }

  /** Cheap client-side checks that catch the most common invalid graphs
   *  (empty / no start / no end) BEFORE hitting the server, so an obviously
   *  un-runnable graph shows a message instantly without a failed POST /run
   *  cluttering the network console. Deeper rules (cycles, reachability) stay
   *  server-side and surface via the 422 ErrorBanner. */
  function precheckGraph(): string[] {
    const errs: string[] = []
    if (nodes.length === 0) {
      errs.push('The workflow is empty: drag nodes from the palette (at least one "start" and one "end").')
      return errs
    }
    const startCount = nodes.filter((n) => n.type === 'start').length
    const endCount = nodes.filter((n) => n.type === 'end').length
    if (startCount !== 1) errs.push(`The graph must have exactly one "start" node (found ${startCount}).`)
    if (endCount < 1) errs.push(`The graph must have at least one "end" node (found ${endCount}).`)
    return errs
  }

  async function handleRun() {
    const payload = tryParseJson(triggerJson)
    if (!payload) {
      setTriggerJsonError('Invalid JSON')
      return
    }
    setTriggerJsonError(null)

    // Pre-validate locally so an empty / start-less graph never fires the request.
    const localErrors = precheckGraph()
    if (localErrors.length > 0) {
      setRunError(localErrors.join('\n'))
      return
    }
    setRunError(null)

    try {
      // Run executes the *saved* graph, so persist the current canvas first —
      // otherwise the user runs a stale graph and gets a confusing 422 for nodes
      // they can see on screen but never saved.
      await persistGraph()
      const run = await runMutation.mutateAsync({ id, payload })
      setShowRunModal(false)
      navigate(`/app/runs/${run.id}`)
    } catch {
      // Deeper validation/run errors are shown by the ErrorBanner via runMutation.isError.
      // Keep the modal open so the user can read the message and fix the graph.
    }
  }

  const selectedNode = nodes.find((n) => n.id === selectedNodeId)
  const dotColor = theme === 'dark' ? '#33343c' : '#d4d4d8'

  if (isLoading) return <LoadingSpinner label="Loading workflow..." />
  if (isError) {
    return (
      <div className="p-container-margin">
        <ErrorBanner message={error instanceof Error ? error.message : 'Failed to load workflow'} />
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Toolbar */}
      <header className="flex shrink-0 flex-wrap items-center gap-3 border-b border-outline-variant bg-surface px-container-margin py-2">
        <button
          onClick={() => navigate('/app')}
          className="flex items-center gap-1 font-mono text-label-xs uppercase tracking-wide text-on-surface-variant transition-colors hover:text-on-surface"
          aria-label="Back to workflows"
        >
          <ArrowLeft size={14} /> Workflows
        </button>

        <input
          type="text"
          value={nameEdit}
          onChange={(e) => setNameEdit(e.target.value)}
          className="min-w-0 max-w-xs flex-1 border-b border-transparent bg-transparent px-1 font-mono text-code-sm font-semibold text-on-surface outline-none hover:border-outline-variant focus:border-primary"
          aria-label="Workflow name"
        />

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {updateMutation.isError && (
            <span className="font-mono text-[10px] text-status-error">
              Save failed: {updateMutation.error instanceof Error ? updateMutation.error.message : 'Unknown error'}
            </span>
          )}
          {updateMutation.isSuccess && <span className="font-mono text-[10px] text-status-success">Saved</span>}

          <button
            onClick={undo}
            disabled={past.current.length === 0}
            className={BTN_ICON}
            title="Undo (Ctrl+Z)"
            aria-label="Undo"
          >
            <Undo2 size={14} />
          </button>
          <button
            onClick={redo}
            disabled={future.current.length === 0}
            className={BTN_ICON}
            title="Redo (Ctrl+Shift+Z)"
            aria-label="Redo"
          >
            <Redo2 size={14} />
          </button>

          <button onClick={() => void handleValidate()} disabled={validateMutation.isPending} className={BTN_SECONDARY}>
            {validateMutation.isPending ? 'Validating…' : 'Validate'}
          </button>
          <button onClick={() => void handleSave()} disabled={updateMutation.isPending} className={BTN_STRONG}>
            {updateMutation.isPending ? 'Saving…' : 'Save'}
          </button>
          <button
            onClick={() => {
              setRunError(null)
              setShowRunModal(true)
            }}
            className={BTN_PRIMARY}
          >
            <Play size={14} /> Run
          </button>
          <ThemeToggle />
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        <NodePalette onAdd={addNode} />

        <main className="relative flex-1 dot-matrix" aria-label="Workflow canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStart={() => takeSnapshot()}
            deleteKeyCode={null}
            multiSelectionKeyCode={['Shift']}
            nodeTypes={NODE_TYPES}
            onNodeClick={(e, node) => {
              // Shift+click is a multi-select gesture — don't hijack it to open
              // the single-node config drawer.
              if (e.shiftKey) return
              setSelectedNodeId(node.id)
            }}
            onPaneClick={() => setSelectedNodeId(null)}
            fitView
            proOptions={{ hideAttribution: false }}
          >
            <Background color={dotColor} gap={16} />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </main>

        {selectedNode && workflow && (
          <NodeConfigDrawer
            node={{
              id: selectedNode.id,
              type: selectedNode.type as NodeType,
              position: selectedNode.position,
              data: selectedNode.data as GraphNode['data'],
            }}
            onUpdate={updateNode}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>

      {/* Validation modal */}
      {validationResult && (
        <Modal open={!!validationResult} onClose={() => setValidationResult(null)} title="Validation Result">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              {validationResult.valid ? (
                <CheckCircle2 size={18} className="text-status-success" />
              ) : (
                <XCircle size={18} className="text-status-error" />
              )}
              <span className="font-mono text-code-sm font-semibold uppercase tracking-wide text-on-surface">
                {validationResult.valid ? 'Graph is valid' : 'Validation failed'}
              </span>
            </div>
            {validationResult.errors.length > 0 && (
              <div>
                <p className="mb-1 font-mono text-label-xs uppercase tracking-wide text-status-error">Errors</p>
                <ul className="space-y-1 font-mono text-label-xs text-on-surface">
                  {validationResult.errors.map((e, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-status-error">›</span>
                      {e}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {validationResult.warnings.length > 0 && (
              <div>
                <p className="mb-1 font-mono text-label-xs uppercase tracking-wide text-status-warning">Warnings</p>
                <ul className="space-y-1 font-mono text-label-xs text-on-surface">
                  {validationResult.warnings.map((w, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-status-warning">›</span>
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {validationResult.errors.length === 0 && validationResult.warnings.length === 0 && (
              <p className="font-mono text-label-xs text-on-surface-variant">No issues found.</p>
            )}
          </div>
        </Modal>
      )}

      {/* Run modal */}
      <Modal open={showRunModal} onClose={() => setShowRunModal(false)} title="Run Workflow">
        <div className="flex flex-col gap-4">
          <div>
            <label htmlFor="trigger-payload" className="mb-2 block font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">
              Trigger Payload (JSON)
            </label>
            <textarea
              id="trigger-payload"
              value={triggerJson}
              onChange={(e) => {
                setTriggerJson(e.target.value)
                setTriggerJsonError(null)
              }}
              rows={8}
              className="w-full resize-y border border-outline-variant bg-surface-container-lowest px-3 py-2 font-mono text-code-sm text-on-surface focus:border-primary focus:outline-none"
              placeholder="{}"
            />
            {triggerJsonError && <p className="mt-1 font-mono text-[10px] text-status-error">{triggerJsonError}</p>}
            <p className="mt-1 font-mono text-[10px] text-on-surface-variant">
              Becomes <code>$.trigger</code> in JSONPath expressions.
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowRunModal(false)} className={BTN_SECONDARY}>
              Cancel
            </button>
            <button onClick={() => void handleRun()} disabled={runMutation.isPending} className={BTN_PRIMARY}>
              <Play size={14} /> {runMutation.isPending ? 'Starting…' : 'Start Run'}
            </button>
          </div>
          {(runError || runMutation.isError) && (
            <ErrorBanner
              message={
                runError ?? (runMutation.error instanceof Error ? runMutation.error.message : 'Run failed')
              }
            />
          )}
        </div>
      </Modal>
    </div>
  )
}
