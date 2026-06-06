import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DebugNode } from './DebugNode'
import type { NodeProps } from '@xyflow/react'

// React Flow's Handle components use ResizeObserver internally
// and need the canvas context. We mock them here.
vi.mock('@xyflow/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@xyflow/react')>()
  return {
    ...actual,
    Handle: ({ type, position }: { type: string; position: string }) => (
      <div data-testid={`handle-${type}-${position}`} />
    ),
    Position: { Top: 'Top', Bottom: 'Bottom' },
  }
})

function makeProps(overrides: Record<string, unknown> = {}): NodeProps {
  return {
    id: 'test-node',
    type: 'debugNode',
    selected: false,
    isConnectable: true,
    zIndex: 0,
    positionAbsoluteX: 0,
    positionAbsoluteY: 0,
    dragging: false,
    draggable: false,
    selectable: true,
    deletable: true,
    data: {
      label: 'My Transform',
      nodeType: 'transform',
      status: 'completed',
      durationMs: 200,
      ...overrides,
    },
  } as unknown as NodeProps
}

describe('DebugNode', () => {
  it('renders the node label', () => {
    render(<DebugNode {...makeProps()} />)
    expect(screen.getByText('My Transform')).toBeTruthy()
  })

  it('renders the status text', () => {
    render(<DebugNode {...makeProps({ status: 'running' })} />)
    expect(screen.getByText('running')).toBeTruthy()
  })

  it('renders duration', () => {
    render(<DebugNode {...makeProps({ durationMs: 1500 })} />)
    expect(screen.getByText('1.5s')).toBeTruthy()
  })

  it('renders pending status when status is pending', () => {
    render(<DebugNode {...makeProps({ status: 'pending' })} />)
    expect(screen.getByText('pending')).toBeTruthy()
  })

  it('renders branch handles for branch node type', () => {
    render(<DebugNode {...makeProps({ nodeType: 'branch', status: 'completed' })} />)
    expect(screen.getByText('true')).toBeTruthy()
    expect(screen.getByText('false')).toBeTruthy()
  })

  it('does not render branch handles for non-branch nodes', () => {
    render(<DebugNode {...makeProps({ nodeType: 'transform', status: 'completed' })} />)
    expect(screen.queryByText('true')).toBeNull()
  })

  it('renders the selection indicator when selected=true', () => {
    const { container } = render(<DebugNode {...makeProps()} selected={true} />)
    // Selection is shown as an inset 1px border overlay (Conductor OS style).
    expect(container.querySelector('.border-primary')).toBeTruthy()
  })
})
