import { describe, expect, it } from 'vitest'
import type { Edge, Node } from '@xyflow/react'
import { layoutGraph } from './layout'

function node(id: string, x = 0, y = 0, type = 'transform'): Node {
  return { id, type, position: { x, y }, data: { label: id, config: {} } }
}
function edge(id: string, source: string, target: string): Edge {
  return { id, source, target }
}

describe('layoutGraph', () => {
  it('spreads a simple chain left-to-right by level', () => {
    const nodes = [node('a'), node('b'), node('c')]
    const edges = [edge('e1', 'a', 'b'), edge('e2', 'b', 'c')]
    const out = layoutGraph(nodes, edges)
    const pos = Object.fromEntries(out.map((n) => [n.id, n.position]))
    expect(pos.a.x).toBeLessThan(pos.b.x)
    expect(pos.b.x).toBeLessThan(pos.c.x)
  })

  it('places all degenerate (same-position) nodes at distinct levels for a chain', () => {
    // Simulates a messy import: every node imported at the same {x, y}.
    const nodes = [node('a', 0, 0), node('b', 0, 0), node('c', 0, 0)]
    const edges = [edge('e1', 'a', 'b'), edge('e2', 'b', 'c')]
    const out = layoutGraph(nodes, edges)
    const xs = out.map((n) => n.position.x)
    expect(new Set(xs).size).toBe(3)
  })

  it('puts fan-out branches on the same level, stacked vertically', () => {
    const nodes = [node('start'), node('true-branch'), node('false-branch'), node('end')]
    const edges = [
      edge('e1', 'start', 'true-branch'),
      edge('e2', 'start', 'false-branch'),
      edge('e3', 'true-branch', 'end'),
      edge('e4', 'false-branch', 'end'),
    ]
    const out = layoutGraph(nodes, edges)
    const pos = Object.fromEntries(out.map((n) => [n.id, n.position]))
    expect(pos['true-branch'].x).toBe(pos['false-branch'].x)
    expect(pos['true-branch'].y).not.toBe(pos['false-branch'].y)
    // "end" must sit after both branches (longest-path level, not first-seen).
    expect(pos.end.x).toBeGreaterThan(pos['true-branch'].x)
  })

  it('is a no-op-safe pass for a single isolated node', () => {
    const out = layoutGraph([node('solo')], [])
    expect(out).toHaveLength(1)
    expect(out[0].position).toEqual({ x: 80, y: 160 })
  })
})
