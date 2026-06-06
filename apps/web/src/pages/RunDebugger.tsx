import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ReactFlow, Background, Controls, type Edge, type Node } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ArrowLeft, ChevronLeft, ChevronRight, Radio, RotateCcw, SkipBack, SkipForward } from 'lucide-react'

import { useReplayRun, useRun, useRunEvents } from '../hooks/useRuns'
import { useWorkflow } from '../hooks/useWorkflows'
import { useRunStream } from '../hooks/useRunStream'
import { computeReplayState } from '../lib/replayState'
import { PayloadInspector } from '../components/ui/PayloadInspector'
import { StatusBadge } from '../components/ui/StatusBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { ThemeToggle } from '../components/ui/ThemeToggle'
import { formatDateTime, formatDuration, cx } from '../lib/utils'
import { useTheme } from '../lib/theme'
import type { ExecutionEventOut, GraphNode, RunOut } from '../types/api'
import { DebugNode } from '../components/flow/DebugNode'

const DEBUG_NODE_TYPES = { debugNode: DebugNode } as const
const EDGE_TRUE = '#22c55e'
const EDGE_FALSE = '#ef4444'

/** "/runs/:id" — Time-Travel Debugger. */
export function RunDebugger() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { theme } = useTheme()

  const { data: run, isLoading: runLoading, isError: runError, error: runErrorObj } = useRun(id)

  const workflowId = run?.workflow_id ?? ''
  const { data: workflow, isLoading: wfLoading } = useWorkflow(workflowId)
  const { data: restEvents } = useRunEvents(id)
  const replayMutation = useReplayRun()

  const isLive = run?.status === 'running' || run?.status === 'pending'
  const { events: wsEvents, connected } = useRunStream(id, { enabled: Boolean(isLive) })

  const allEvents: ExecutionEventOut[] = useMemo(() => {
    const base = restEvents ?? []
    const byId = new Map<string, ExecutionEventOut>()
    for (const e of base) byId.set(e.id, e)
    for (const e of wsEvents) if (!byId.has(e.id)) byId.set(e.id, e)
    return Array.from(byId.values()).sort((a, b) => a.sequence - b.sequence)
  }, [restEvents, wsEvents])

  const [scrubK, setScrubK] = useState<number>(-1)

  useEffect(() => {
    if (isLive && allEvents.length > 0) setScrubK(allEvents.length - 1)
  }, [isLive, allEvents.length])

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const nodeIds = useMemo(() => (workflow?.graph.nodes ?? []).map((n) => n.id), [workflow])
  const replayStateMap = useMemo(() => computeReplayState(allEvents, scrubK, nodeIds), [allEvents, scrubK, nodeIds])

  const flowNodes: Node[] = useMemo(() => {
    if (!workflow) return []
    return workflow.graph.nodes.map((gn: GraphNode) => {
      const rs = replayStateMap.get(gn.id)
      return {
        id: gn.id,
        type: 'debugNode',
        position: gn.position,
        data: {
          label: gn.data.label,
          nodeType: gn.type,
          status: rs?.status ?? 'pending',
          durationMs: rs?.event?.duration_ms ?? null,
        },
      }
    })
  }, [workflow, replayStateMap])

  const flowEdges: Edge[] = useMemo(() => {
    if (!workflow) return []
    return workflow.graph.edges.map((ge) => ({
      id: ge.id,
      source: ge.source,
      target: ge.target,
      sourceHandle: ge.data?.branch ?? null,
      label: ge.data?.branch,
      style:
        ge.data?.branch === 'true'
          ? { stroke: EDGE_TRUE }
          : ge.data?.branch === 'false'
            ? { stroke: EDGE_FALSE }
            : undefined,
    }))
  }, [workflow])

  const inspectorEvent = useMemo((): ExecutionEventOut | null => {
    if (!selectedNodeId) return allEvents[scrubK] ?? null
    const rs = replayStateMap.get(selectedNodeId)
    return rs?.event ?? null
  }, [selectedNodeId, scrubK, allEvents, replayStateMap])

  const onNodeClick = useCallback((_: unknown, node: Node) => {
    setSelectedNodeId((prev) => (prev === node.id ? null : node.id))
  }, [])

  async function handleReplay() {
    try {
      const newRun = await replayMutation.mutateAsync(id)
      navigate(`/runs/${newRun.id}`)
    } catch {
      // Surfaced via replayMutation state; swallow to avoid an unhandled rejection.
    }
  }

  if (runLoading || wfLoading) return <LoadingSpinner label="Loading run..." />
  if (runError) {
    return (
      <div className="p-container-margin">
        <ErrorBanner message={runErrorObj instanceof Error ? runErrorObj.message : 'Failed to load run'} />
      </div>
    )
  }

  const runData: RunOut = run as RunOut
  const maxK = allEvents.length - 1
  const dotColor = theme === 'dark' ? '#33343c' : '#d4d4d8'

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex shrink-0 flex-wrap items-center gap-3 border-b border-outline-variant bg-surface px-container-margin py-2">
        <button
          onClick={() => navigate(`/workflows/${runData.workflow_id}`)}
          className="flex items-center gap-1 font-mono text-label-xs uppercase tracking-wide text-on-surface-variant transition-colors hover:text-on-surface"
        >
          <ArrowLeft size={14} /> Editor
        </button>

        <div className="flex min-w-0 flex-1 items-center gap-2">
          <h1 className="truncate font-mono text-code-sm font-semibold text-on-surface">{workflow?.name ?? 'Loading…'}</h1>
          <StatusBadge status={runData.status} />
          {isLive && connected && (
            <span className="inline-flex items-center gap-1 font-mono text-label-xs uppercase tracking-wide text-status-running">
              <Radio size={12} className="animate-pulse" /> Live
            </span>
          )}
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span className="font-mono text-label-xs text-on-surface-variant">
            {allEvents.length} event{allEvents.length !== 1 ? 's' : ''}
          </span>
          <button
            onClick={() => void handleReplay()}
            disabled={replayMutation.isPending}
            className="flex items-center gap-1.5 border border-primary bg-primary px-3 py-1 font-mono text-label-xs font-bold uppercase tracking-wide text-on-primary transition-colors hover:bg-transparent hover:text-on-surface disabled:opacity-60"
          >
            <RotateCcw size={14} /> {replayMutation.isPending ? 'Replaying…' : 'Replay'}
          </button>
          <ThemeToggle />
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <main className="flex flex-1 flex-col overflow-hidden border-r border-outline-variant">
          <div className="relative flex-1 dot-matrix">
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              nodeTypes={DEBUG_NODE_TYPES}
              onNodeClick={onNodeClick}
              onPaneClick={() => setSelectedNodeId(null)}
              fitView
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable
              proOptions={{ hideAttribution: false }}
            >
              <Background color={dotColor} gap={16} />
              <Controls />
            </ReactFlow>
          </div>

          {/* Timeline scrubber */}
          <div className="flex flex-col gap-2 border-t border-outline-variant bg-surface px-container-margin py-3">
            <div className="flex items-center justify-between font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">
              <span>// Timeline</span>
              <span>
                Step {scrubK + 1} / {Math.max(allEvents.length, 1)}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <ScrubButton label="First" onClick={() => setScrubK(-1)}>
                <SkipBack size={14} />
              </ScrubButton>
              <ScrubButton label="Prev" onClick={() => setScrubK((k) => Math.max(-1, k - 1))}>
                <ChevronLeft size={14} />
              </ScrubButton>

              <input
                type="range"
                min={-1}
                max={maxK}
                value={scrubK}
                onChange={(e) => setScrubK(parseInt(e.target.value, 10))}
                className="flex-1"
                aria-label="Timeline scrubber"
              />

              <ScrubButton label="Next" onClick={() => setScrubK((k) => Math.min(maxK, k + 1))}>
                <ChevronRight size={14} />
              </ScrubButton>
              <ScrubButton label="Last" onClick={() => setScrubK(maxK)}>
                <SkipForward size={14} />
              </ScrubButton>
            </div>

            <EventTimeline events={allEvents} currentK={scrubK} onSelect={setScrubK} />
          </div>
        </main>

        {/* Inspector panel */}
        <aside className="flex w-80 shrink-0 flex-col overflow-hidden bg-surface" aria-label="Payload inspector">
          <div className="border-b border-outline-variant bg-surface-container-lowest px-4 py-3">
            <h2 className="font-mono text-code-sm font-bold uppercase tracking-wide text-on-surface">
              Inspector{selectedNodeId ? ` // ${selectedNodeId}` : ''}
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto">
            <PayloadInspector event={inspectorEvent} nodeId={selectedNodeId ?? undefined} />
          </div>

          <div className="space-y-1 border-t border-outline-variant p-4 font-mono text-label-xs text-on-surface-variant">
            <div className="flex justify-between">
              <span>Started</span>
              <span className="text-on-surface">{formatDateTime(runData.started_at)}</span>
            </div>
            <div className="flex justify-between">
              <span>Finished</span>
              <span className="text-on-surface">{formatDateTime(runData.finished_at)}</span>
            </div>
            {runData.error && <p className="mt-1 break-words text-status-error">{runData.error}</p>}
          </div>
        </aside>
      </div>
    </div>
  )
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function ScrubButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      className="flex h-7 w-7 items-center justify-center border border-outline-variant text-on-surface-variant transition-colors hover:border-primary hover:text-on-surface"
    >
      {children}
    </button>
  )
}

interface EventTimelineProps {
  events: ExecutionEventOut[]
  currentK: number
  onSelect: (k: number) => void
}

function EventTimeline({ events, currentK, onSelect }: EventTimelineProps) {
  const STATUS_DOT: Record<string, string> = {
    running: 'bg-status-running',
    completed: 'bg-status-success',
    failed: 'bg-status-error',
    skipped: 'bg-on-surface-variant',
  }

  if (events.length === 0) {
    return (
      <p className="py-2 text-center font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">
        No events yet
      </p>
    )
  }

  return (
    <div className="flex gap-1 overflow-x-auto pb-1" role="list" aria-label="Event timeline">
      {events.map((ev, i) => {
        const isCurrent = i === currentK
        const isPast = i <= currentK
        return (
          <button
            key={ev.id}
            onClick={() => onSelect(i)}
            role="listitem"
            aria-label={`Event ${i + 1}: ${ev.node_id} — ${ev.status}`}
            aria-current={isCurrent ? 'step' : undefined}
            className={cx(
              'flex shrink-0 flex-col items-center gap-1 border px-1.5 py-1 font-mono text-[10px] transition-colors',
              isCurrent
                ? 'border-primary bg-surface-container-high'
                : isPast
                  ? 'border-outline-variant bg-surface-container-low'
                  : 'border-transparent opacity-40',
            )}
          >
            <span className={cx('h-1.5 w-1.5', STATUS_DOT[ev.status] ?? 'bg-on-surface-variant')} />
            <span className="max-w-[48px] truncate text-on-surface-variant" title={ev.node_id}>
              {ev.node_id.slice(0, 6)}
            </span>
            {ev.duration_ms != null && <span className="text-on-surface-variant">{formatDuration(ev.duration_ms)}</span>}
          </button>
        )
      })}
    </div>
  )
}
