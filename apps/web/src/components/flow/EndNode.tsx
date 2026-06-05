import type { NodeProps } from '@xyflow/react'
import { BaseNode } from './BaseNode'
import { NODE_META } from './nodeMeta'

export function EndNode({ selected }: NodeProps) {
  return (
    <BaseNode
      label="End"
      icon={NODE_META.end.icon}
      tag={NODE_META.end.tag}
      hasOutput={false}
      selected={selected}
    >
      <span className="text-on-surface-variant">collects final payload</span>
    </BaseNode>
  )
}
