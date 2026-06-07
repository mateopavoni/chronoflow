import { ArrowRightLeft, Globe, Play, Split, Square, Timer, type LucideIcon } from 'lucide-react'
import type { NodeType } from '../../types/api'

/** Shared per-node-type metadata: lucide icon + uppercase type tag. */
export const NODE_META: Record<NodeType, { icon: LucideIcon; tag: string }> = {
  start: { icon: Play, tag: 'START' },
  end: { icon: Square, tag: 'END' },
  transform: { icon: ArrowRightLeft, tag: 'TRANSFORM' },
  http: { icon: Globe, tag: 'HTTP' },
  delay: { icon: Timer, tag: 'DELAY' },
  branch: { icon: Split, tag: 'BRANCH' },
}

/** Shared className for React Flow connection handles — square, monochrome. */
export const HANDLE_CLASS =
  '!w-2.5 !h-2.5 !rounded-none !bg-surface !border !border-outline'
