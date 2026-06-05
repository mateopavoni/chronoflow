import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2 } from 'lucide-react'
import { useCreateWorkflow, useDeleteWorkflow, useWorkflows } from '../hooks/useWorkflows'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { EmptyState } from '../components/ui/EmptyState'
import { Modal } from '../components/ui/Modal'
import { formatDateTime } from '../lib/utils'
import type { WorkflowOut } from '../types/api'

/**
 * "/" — Workflow list page (Conductor OS high-density table).
 * "New Workflow" creates a minimal start→end graph and opens the editor.
 */
export function Workflows() {
  const navigate = useNavigate()
  const { data: workflows, isLoading, isError, error, refetch } = useWorkflows()
  const createMutation = useCreateWorkflow()
  const deleteMutation = useDeleteWorkflow()
  const [pendingDelete, setPendingDelete] = useState<WorkflowOut | null>(null)

  async function handleNewWorkflow() {
    const result = await createMutation.mutateAsync({
      name: 'Untitled Workflow',
      description: '',
      graph: {
        nodes: [
          { id: 'start-1', type: 'start', position: { x: 250, y: 50 }, data: { label: 'Start', config: {} } },
          { id: 'end-1', type: 'end', position: { x: 250, y: 200 }, data: { label: 'End', config: {} } },
        ],
        edges: [{ id: 'e-start-end', source: 'start-1', target: 'end-1' }],
      },
    })
    navigate(`/workflows/${result.id}`)
  }

  function requestDelete(workflow: WorkflowOut, e: React.MouseEvent) {
    e.stopPropagation()
    deleteMutation.reset() // clear any stale error from a previous attempt
    setPendingDelete(workflow)
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    try {
      await deleteMutation.mutateAsync(pendingDelete.id)
      setPendingDelete(null)
    } catch {
      // Keep the modal open; the failure is surfaced via deleteMutation.isError below.
    }
  }

  if (isLoading) return <LoadingSpinner label="Loading workflows..." />

  if (isError) {
    return (
      <div className="p-container-margin">
        <ErrorBanner
          message={error instanceof Error ? error.message : 'Failed to load workflows'}
          onRetry={() => void refetch()}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl p-container-margin">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between border-b border-outline-variant pb-4">
        <div>
          <h1 className="font-mono text-headline-md uppercase tracking-tight text-on-surface">// Workflows Hub</h1>
          <p className="mt-1 font-mono text-label-xs text-on-surface-variant">Design and run event-driven DAG workflows</p>
        </div>
        <button
          onClick={() => void handleNewWorkflow()}
          disabled={createMutation.isPending}
          className="flex items-center gap-2 border border-primary bg-primary px-4 py-1.5 font-mono text-label-xs font-bold uppercase tracking-wide text-on-primary transition-colors hover:bg-transparent hover:text-on-surface disabled:opacity-60"
        >
          <Plus size={14} />
          {createMutation.isPending ? 'Creating…' : 'New Workflow'}
        </button>
      </div>

      {/* Table */}
      {!workflows || workflows.length === 0 ? (
        <EmptyState
          title="No workflows yet"
          description="Create your first workflow to get started designing event-driven DAGs."
          action={
            <button
              onClick={() => void handleNewWorkflow()}
              className="border border-primary bg-primary px-4 py-1.5 font-mono text-label-xs font-bold uppercase tracking-wide text-on-primary transition-colors hover:bg-transparent hover:text-on-surface"
            >
              Create workflow
            </button>
          }
        />
      ) : (
        <div className="border border-outline-variant">
          {/* Table header */}
          <div className="grid grid-cols-[2.5fr_0.7fr_1.3fr_0.5fr] border-b border-outline-variant bg-surface-container-low font-mono text-label-xs uppercase tracking-wider text-on-surface-variant">
            <div className="border-r border-outline-variant px-cell-padding-x py-cell-padding-y">Workflow Name</div>
            <div className="border-r border-outline-variant px-cell-padding-x py-cell-padding-y">Nodes</div>
            <div className="border-r border-outline-variant px-cell-padding-x py-cell-padding-y">Updated</div>
            <div className="px-cell-padding-x py-cell-padding-y text-center">·</div>
          </div>

          {/* Rows */}
          <ul role="list">
            {workflows.map((wf) => (
              <WorkflowRow
                key={wf.id}
                workflow={wf}
                onClick={() => navigate(`/workflows/${wf.id}`)}
                onDelete={(e) => requestDelete(wf, e)}
                deleting={deleteMutation.isPending && deleteMutation.variables === wf.id}
              />
            ))}
          </ul>
        </div>
      )}

      {createMutation.isError && (
        <div className="mt-4">
          <ErrorBanner
            message={createMutation.error instanceof Error ? createMutation.error.message : 'Create failed'}
          />
        </div>
      )}

      {/* Delete confirmation */}
      <Modal
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Delete workflow"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <p className="text-body-sm text-on-surface">
            Delete <span className="font-semibold">{pendingDelete?.name}</span>? This action cannot be undone.
          </p>
          {deleteMutation.isError && (
            <ErrorBanner
              message={deleteMutation.error instanceof Error ? deleteMutation.error.message : 'Delete failed'}
            />
          )}
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setPendingDelete(null)}
              className="border border-outline-variant px-3 py-1 font-mono text-label-xs uppercase tracking-wide text-on-surface-variant transition-colors hover:border-primary hover:text-on-surface"
            >
              Cancel
            </button>
            <button
              onClick={() => void confirmDelete()}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-1.5 border border-status-error bg-status-error px-3 py-1 font-mono text-label-xs font-bold uppercase tracking-wide text-on-primary transition-colors hover:bg-transparent hover:text-status-error disabled:opacity-60"
            >
              <Trash2 size={14} /> {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

// ─── WorkflowRow ────────────────────────────────────────────────────────────────

interface WorkflowRowProps {
  workflow: WorkflowOut
  onClick: () => void
  onDelete: (e: React.MouseEvent) => void
  deleting: boolean
}

function WorkflowRow({ workflow, onClick, onDelete, deleting }: WorkflowRowProps) {
  const nodeCount = workflow.graph.nodes.length

  return (
    <li
      onClick={onClick}
      className="group grid cursor-pointer grid-cols-[2.5fr_0.7fr_1.3fr_0.5fr] border-b border-outline-variant bg-surface transition-colors last:border-b-0 hover:bg-surface-container-highest"
      aria-label={`Open workflow: ${workflow.name}`}
    >
      <div className="flex min-w-0 flex-col justify-center border-r border-outline-variant px-cell-padding-x py-cell-padding-y">
        <span className="truncate text-body-sm font-semibold text-on-surface">{workflow.name}</span>
        {workflow.description && (
          <span className="truncate font-mono text-[10px] text-on-surface-variant">{workflow.description}</span>
        )}
      </div>
      <div className="flex items-center border-r border-outline-variant px-cell-padding-x py-cell-padding-y font-mono text-code-sm text-on-surface-variant">
        {nodeCount}
      </div>
      <div className="flex items-center border-r border-outline-variant px-cell-padding-x py-cell-padding-y font-mono text-code-sm text-on-surface-variant">
        {formatDateTime(workflow.updated_at)}
      </div>
      <div className="flex items-center justify-center px-cell-padding-x py-cell-padding-y">
        <button
          onClick={onDelete}
          disabled={deleting}
          aria-label={`Delete workflow: ${workflow.name}`}
          className="flex h-6 w-6 items-center justify-center text-on-surface-variant transition-colors hover:text-status-error disabled:opacity-40"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </li>
  )
}
