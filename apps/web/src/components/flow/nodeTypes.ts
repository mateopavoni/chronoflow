// Registry of all custom node components for React Flow's nodeTypes prop
// Import here to keep App.tsx clean and allow lazy-loading in the future.

import { StartNode } from './StartNode'
import { EndNode } from './EndNode'
import { TransformNode } from './TransformNode'
import { HttpNode } from './HttpNode'
import { DelayNode } from './DelayNode'
import { BranchNode } from './BranchNode'

// React Flow expects a stable object (not recreated each render) for nodeTypes.
// Defining it here at module level guarantees that.
export const NODE_TYPES = {
  start: StartNode,
  end: EndNode,
  transform: TransformNode,
  http: HttpNode,
  delay: DelayNode,
  branch: BranchNode,
} as const
