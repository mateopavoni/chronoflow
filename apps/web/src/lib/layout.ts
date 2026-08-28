import type { Edge, Node } from '@xyflow/react'

const LEVEL_START = 80
const SIBLING_START = 160
const LEVEL_STEP = 240
const SIBLING_STEP = 140

/**
 * Lay out nodes by topological level (longest path from the roots — nodes
 * with no incoming edges), one column/row per level.
 *
 * direction 'horizontal' (default): level → X, siblings stacked on Y (left-to-right flow).
 * direction 'vertical': level → Y, siblings spread on X (top-to-bottom flow).
 *
 * no real graph-layout library (no dagre/elkjs dependency) — this
 * is a plain Kahn's-algorithm pass, good enough for this project's simple
 * DAGs (mostly chains, occasional branch/fan-in). A graph with heavy branch
 * crossing will still look busy; swap in a real layout lib if that becomes
 * a real complaint. Cycles aren't handled (the validator already rejects
 * them before a graph can be saved/run) — any node a cycle leaves unreached
 * just falls back to level 0.
 */
export function layoutGraph(
  nodes: Node[],
  edges: Edge[],
  direction: 'vertical' | 'horizontal' = 'horizontal',
): Node[] {
  const remaining = new Map<string, number>()
  const outgoing = new Map<string, string[]>()
  for (const n of nodes) {
    remaining.set(n.id, 0)
    outgoing.set(n.id, [])
  }
  for (const e of edges) {
    if (!outgoing.has(e.source) || !remaining.has(e.target)) continue
    outgoing.get(e.source)!.push(e.target)
    remaining.set(e.target, (remaining.get(e.target) ?? 0) + 1)
  }

  const level = new Map<string, number>()
  const queue: string[] = []
  for (const n of nodes) {
    if (remaining.get(n.id) === 0) {
      level.set(n.id, 0)
      queue.push(n.id)
    }
  }

  for (let head = 0; head < queue.length; head++) {
    const id = queue[head]!
    const l = level.get(id) ?? 0
    for (const next of outgoing.get(id) ?? []) {
      level.set(next, Math.max(level.get(next) ?? 0, l + 1))
      const left = (remaining.get(next) ?? 0) - 1
      remaining.set(next, left)
      if (left === 0) queue.push(next)
    }
  }

  // Nodes a cycle kept out of the queue never got a level — default to 0.
  for (const n of nodes) if (!level.has(n.id)) level.set(n.id, 0)

  const perLevelCount = new Map<number, number>()
  return nodes.map((n) => {
    const l = level.get(n.id) ?? 0
    const i = perLevelCount.get(l) ?? 0
    perLevelCount.set(l, i + 1)
    const levelPos = LEVEL_START + l * LEVEL_STEP
    const siblingPos = SIBLING_START + i * SIBLING_STEP
    const position = direction === 'vertical' ? { x: siblingPos, y: levelPos } : { x: levelPos, y: siblingPos }
    return { ...n, position }
  })
}
