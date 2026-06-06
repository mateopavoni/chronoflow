import type { EventStatus, ExecutionEventOut } from '../types/api'

/**
 * The state of a single node at a given replay instant.
 * Built by applying execution events 0..k.
 */
export interface NodeReplayState {
  nodeId: string
  /** Latest status at instant k. undefined = not yet reached. */
  status: EventStatus | undefined
  /** The event responsible for the current status (latest one for this node at ≤k) */
  event: ExecutionEventOut | undefined
}

/**
 * Result of applying events[0..k] (inclusive) over the node list.
 * Pure function — no side effects, easily testable.
 *
 * @param events   Full ordered list of ExecutionEventOut (by sequence ascending)
 * @param k        Scrubber position: apply events[0] through events[k] inclusive (0-based index)
 * @param nodeIds  All node IDs in the workflow graph
 */
export function computeReplayState(
  events: ExecutionEventOut[],
  k: number,
  nodeIds: string[],
): Map<string, NodeReplayState> {
  const result = new Map<string, NodeReplayState>()

  // Initialize every node as pending/unreached
  for (const id of nodeIds) {
    result.set(id, { nodeId: id, status: undefined, event: undefined })
  }

  // Apply events 0..k
  const limit = Math.min(k, events.length - 1)
  for (let i = 0; i <= limit; i++) {
    const ev = events[i]
    if (!ev) continue

    const current = result.get(ev.node_id)
    // Each event overwrites the previous status for a node.
    // The last event at or before k is the authoritative one.
    result.set(ev.node_id, {
      nodeId: ev.node_id,
      status: ev.status,
      event: ev,
    })

    // Suppress TS unused-variable warning
    void current
  }

  return result
}

/**
 * Tailwind color classes for each event status used in the DAG visualization.
 */
export const STATUS_COLORS: Record<EventStatus | 'pending', string> = {
  pending: 'bg-gray-100 border-gray-300 text-gray-500',
  running: 'bg-blue-100 border-blue-400 text-blue-700',
  completed: 'bg-green-100 border-green-500 text-green-800',
  failed: 'bg-red-100 border-red-500 text-red-800',
  skipped: 'bg-gray-200 border-gray-400 text-gray-500',
}

/**
 * Returns the label displayed on a status badge.
 */
export function statusLabel(status: EventStatus | undefined): string {
  if (!status) return 'pending'
  return status
}
