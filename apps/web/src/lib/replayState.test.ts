import { describe, it, expect } from 'vitest'
import { computeReplayState } from './replayState'
import type { ExecutionEventOut } from '../types/api'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeEvent(
  overrides: Partial<ExecutionEventOut> & { node_id: string; sequence: number },
): ExecutionEventOut {
  return {
    id: `evt-${overrides.sequence}`,
    run_id: 'run-1',
    status: 'completed',
    input_snapshot: {},
    output: null,
    error: null,
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    duration_ms: 100,
    ...overrides,
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('computeReplayState', () => {
  const nodeIds = ['start-1', 'transform-1', 'end-1']

  it('returns all nodes as pending when k is -1 (before any event)', () => {
    const events: ExecutionEventOut[] = [
      makeEvent({ node_id: 'start-1', sequence: 0, status: 'completed' }),
    ]
    const state = computeReplayState(events, -1, nodeIds)

    expect(state.get('start-1')?.status).toBeUndefined()
    expect(state.get('transform-1')?.status).toBeUndefined()
    expect(state.get('end-1')?.status).toBeUndefined()
  })

  it('applies only events up to k (inclusive)', () => {
    const events: ExecutionEventOut[] = [
      makeEvent({ node_id: 'start-1', sequence: 0, status: 'completed' }),
      makeEvent({ node_id: 'transform-1', sequence: 1, status: 'running' }),
      makeEvent({ node_id: 'transform-1', sequence: 2, status: 'completed' }),
      makeEvent({ node_id: 'end-1', sequence: 3, status: 'completed' }),
    ]

    // At k=1: start-1=completed, transform-1=running, end-1=pending
    const state1 = computeReplayState(events, 1, nodeIds)
    expect(state1.get('start-1')?.status).toBe('completed')
    expect(state1.get('transform-1')?.status).toBe('running')
    expect(state1.get('end-1')?.status).toBeUndefined()

    // At k=2: transform-1 should now be completed
    const state2 = computeReplayState(events, 2, nodeIds)
    expect(state2.get('transform-1')?.status).toBe('completed')
  })

  it('correctly handles skipped nodes', () => {
    const skippedEvent = makeEvent({ node_id: 'end-1', sequence: 1, status: 'skipped' })
    const events = [
      makeEvent({ node_id: 'start-1', sequence: 0, status: 'completed' }),
      skippedEvent,
    ]
    const state = computeReplayState(events, 1, nodeIds)
    expect(state.get('end-1')?.status).toBe('skipped')
    expect(state.get('end-1')?.event).toEqual(skippedEvent)
  })

  it('handles nodes not in the workflow gracefully', () => {
    const events = [
      makeEvent({ node_id: 'unknown-node', sequence: 0, status: 'completed' }),
    ]
    // Should not throw; known nodes remain pending
    const state = computeReplayState(events, 0, nodeIds)
    expect(state.get('start-1')?.status).toBeUndefined()
  })

  it('handles empty events array', () => {
    const state = computeReplayState([], 0, nodeIds)
    for (const id of nodeIds) {
      expect(state.get(id)?.status).toBeUndefined()
    }
  })

  it('k beyond events.length applies all events', () => {
    const events: ExecutionEventOut[] = [
      makeEvent({ node_id: 'start-1', sequence: 0, status: 'completed' }),
      makeEvent({ node_id: 'end-1', sequence: 1, status: 'completed' }),
    ]
    // k=999 should just apply all 2 events
    const state = computeReplayState(events, 999, nodeIds)
    expect(state.get('start-1')?.status).toBe('completed')
    expect(state.get('end-1')?.status).toBe('completed')
  })

  it('last event for a node wins when multiple events exist for the same node', () => {
    const events: ExecutionEventOut[] = [
      makeEvent({ node_id: 'transform-1', sequence: 0, status: 'running' }),
      makeEvent({ node_id: 'transform-1', sequence: 1, status: 'failed' }),
    ]
    const state = computeReplayState(events, 1, nodeIds)
    // The last applied event for this node is status=failed
    expect(state.get('transform-1')?.status).toBe('failed')
  })

  it('preserves the event reference on the state entry', () => {
    const ev = makeEvent({ node_id: 'start-1', sequence: 0, status: 'completed', duration_ms: 42 })
    const state = computeReplayState([ev], 0, nodeIds)
    expect(state.get('start-1')?.event).toBe(ev)
    expect(state.get('start-1')?.event?.duration_ms).toBe(42)
  })
})
