import type { NodeProps } from '@xyflow/react'
import { BaseNode } from './BaseNode'
import { NODE_META } from './nodeMeta'

export function StartNode({ selected }: NodeProps) {
  return (
    <BaseNode
      label="Start"
      icon={NODE_META.start.icon}
      tag={NODE_META.start.tag}
      hasInput={false}
      selected={selected}
    >
      <span className="text-on-surface-variant">trigger payload</span>
    </BaseNode>
  )
}
