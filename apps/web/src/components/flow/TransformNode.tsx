import type { NodeProps } from '@xyflow/react'
import { BaseNode } from './BaseNode'
import { NODE_META } from './nodeMeta'
import type { TransformConfig } from '../../types/api'

export function TransformNode({ data, selected }: NodeProps) {
  const config = data?.['config'] as TransformConfig | undefined
  const mappingCount = config?.mappings ? Object.keys(config.mappings).length : 0

  return (
    <BaseNode
      label={typeof data?.['label'] === 'string' ? data['label'] : 'Transform'}
      icon={NODE_META.transform.icon}
      tag={NODE_META.transform.tag}
      selected={selected}
    >
      <div className="flex justify-between">
        <span>mappings</span>
        <span className="text-on-surface">{mappingCount}</span>
      </div>
    </BaseNode>
  )
}
