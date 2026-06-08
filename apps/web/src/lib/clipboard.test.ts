import { describe, expect, it } from 'vitest'
import type { Edge, Node } from '@xyflow/react'
import { cloneWithNewIds, extractSelection } from './clipboard'

function node(id: string, selected: boolean, type = 'transform'): Node {
  return { id, type, position: { x: 100, y: 100 }, data: { label: id, config: {} }, selected }
}
function edge(id: string, source: string, target: string): Edge {
  return { id, source, target }
}

describe('extractSelection', () => {
  it('returns only the selected nodes', () => {
    const nodes = [node('a', true), node('b', false), node('c', true)]
    const { nodes: sel } = extractSelection(nodes, [])
    expect(sel.map((n) => n.id)).toEqual(['a', 'c'])
  })

  it('keeps only edges whose both endpoints are selected', () => {
    const nodes = [node('a', true), node('b', true), node('c', false)]
    const edges = [
      edge('e1', 'a', 'b'), // both selected → kept
      edge('e2', 'b', 'c'), // c not selected → dropped
    ]
    const { edges: inner } = extractSelection(nodes, edges)
    expect(inner.map((e) => e.id)).toEqual(['e1'])
  })

  it('returns empty when nothing is selected', () => {
    const out = extractSelection([node('a', false)], [])
    expect(out.nodes).toHaveLength(0)
    expect(out.edges).toHaveLength(0)
  })
})

describe('cloneWithNewIds', () => {
  it('assigns fresh ids and rewires edges to them', () => {
    let i = 0
    const genId = () => `id${++i}`
    const clip = { nodes: [node('a', true), node('b', true)], edges: [edge('e1', 'a', 'b')] }

    const out = cloneWithNewIds(clip, { genId })

    // node ids regenerated, none equal to the originals
    expect(out.nodes.map((n) => n.id)).not.toContain('a')
    expect(out.nodes.map((n) => n.id)).not.toContain('b')
    // edge rewired to the new node ids
    const [srcId, tgtId] = [out.nodes[0]!.id, out.nodes[1]!.id]
    expect(out.edges[0]!.source).toBe(srcId)
    expect(out.edges[0]!.target).toBe(tgtId)
    expect(out.edges[0]!.id).not.toBe('e1')
  })

  it('offsets positions and pre-selects pasted nodes', () => {
    const clip = { nodes: [node('a', true)], edges: [] }
    const out = cloneWithNewIds(clip, { genId: () => 'x', offset: 25 })
    expect(out.nodes[0]!.position).toEqual({ x: 125, y: 125 })
    expect(out.nodes[0]!.selected).toBe(true)
  })

  it('deep-clones node data so edits do not leak back to the source', () => {
    const src = node('a', true)
    const out = cloneWithNewIds({ nodes: [src], edges: [] }, { genId: () => 'x' })
    ;(out.nodes[0]!.data as { config: Record<string, unknown> }).config.changed = true
    expect((src.data as { config: Record<string, unknown> }).config).toEqual({})
  })
})
