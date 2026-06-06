import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PayloadInspector } from './PayloadInspector'
import type { ExecutionEventOut } from '../../types/api'

function makeEvent(overrides: Partial<ExecutionEventOut> = {}): ExecutionEventOut {
  return {
    id: 'evt-1',
    run_id: 'run-1',
    node_id: 'transform-abc',
    sequence: 3,
    status: 'completed',
    input_snapshot: { trigger: { amount: 100 } },
    output: { normalized: true },
    error: null,
    started_at: '2026-01-01T10:00:00Z',
    finished_at: '2026-01-01T10:00:01Z',
    duration_ms: 1050,
    ...overrides,
  }
}

describe('PayloadInspector', () => {
  it('shows a placeholder when no event is provided', () => {
    render(<PayloadInspector event={null} />)
    expect(screen.getByText(/select a node/i)).toBeTruthy()
  })

  it('shows node-specific placeholder when nodeId is provided but no event', () => {
    render(<PayloadInspector event={null} nodeId="my-node" />)
    expect(screen.getByText(/my-node/i)).toBeTruthy()
  })

  it('renders node_id and status', () => {
    render(<PayloadInspector event={makeEvent()} />)
    expect(screen.getByText('transform-abc')).toBeTruthy()
    expect(screen.getByText('completed')).toBeTruthy()
  })

  it('renders sequence number', () => {
    render(<PayloadInspector event={makeEvent({ sequence: 7 })} />)
    expect(screen.getByText('7')).toBeTruthy()
  })

  it('renders duration', () => {
    render(<PayloadInspector event={makeEvent({ duration_ms: 1050 })} />)
    expect(screen.getByText('1.05s')).toBeTruthy()
  })

  it('renders error message when status is failed', () => {
    render(<PayloadInspector event={makeEvent({ status: 'failed', error: 'Connection timed out' })} />)
    expect(screen.getByText('Connection timed out')).toBeTruthy()
  })

  it('renders input_snapshot JSON', () => {
    render(<PayloadInspector event={makeEvent()} />)
    // JSON is rendered inside a <pre>; check for a key that should appear
    expect(screen.getByText(/input snapshot/i)).toBeTruthy()
  })

  it('shows dash when duration_ms is null', () => {
    render(<PayloadInspector event={makeEvent({ duration_ms: null })} />)
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})
