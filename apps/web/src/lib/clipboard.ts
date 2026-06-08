import type { Edge, Node } from '@xyflow/react'

/** A copied selection of nodes + the edges that live entirely inside it. */
export interface ClipboardData {
  nodes: Node[]
  edges: Edge[]
}

/**
 * Pull the currently-selected nodes out of the canvas, plus only the edges
 * whose *both* endpoints are inside the selection (dangling edges to outside
 * nodes are dropped — they'd point to nodes the paste won't recreate).
 */
export function extractSelection(nodes: Node[], edges: Edge[]): ClipboardData {
  const selected = nodes.filter((n) => n.selected)
  const ids = new Set(selected.map((n) => n.id))
  const innerEdges = edges.filter((e) => ids.has(e.source) && ids.has(e.target))
  return { nodes: selected, edges: innerEdges }
}

/**
 * Clone a clipboard selection with fresh ids so it can be pasted without
 * colliding with the originals. Node ids are remapped, edges are rewired to
 * the new ids, every node is offset and marked `selected` (so the paste lands
 * pre-selected and ready to drag), and node `data` is deep-cloned so config
 * edits on the copy don't leak back into the source.
 *
 * `genId` is injected so callers (and tests) control id generation.
 */
export function cloneWithNewIds(
  clip: ClipboardData,
  opts: { genId: () => string; offset?: number },
): ClipboardData {
  const offset = opts.offset ?? 40
  const idMap = new Map<string, string>()

  const nodes = clip.nodes.map((n) => {
    const id = `${n.type ?? 'node'}-${opts.genId()}`
    idMap.set(n.id, id)
    return {
      ...n,
      id,
      position: { x: n.position.x + offset, y: n.position.y + offset },
      selected: true,
      data: structuredClone(n.data),
    }
  })

  const edges = clip.edges.map((e) => ({
    ...e,
    id: `edge-${opts.genId()}`,
    source: idMap.get(e.source) ?? e.source,
    target: idMap.get(e.target) ?? e.target,
    selected: false,
  }))

  return { nodes, edges }
}
