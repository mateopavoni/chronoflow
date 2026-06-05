import type { NodeProps } from '@xyflow/react'
import { BaseNode } from './BaseNode'
import { NODE_META } from './nodeMeta'
import type { DelayConfig } from '../../types/api'

export function DelayNode({ data, selected }: NodeProps) {
  const config = data?.['config'] as DelayConfig | undefined
  const seconds = config?.seconds ?? 0

  return (
    <BaseNode
      label={typeof data?.['label'] === 'string' ? data['label'] : 'Delay'}
      icon={NODE_META.delay.icon}
      tag={NODE_META.delay.tag}
      selected={selected}
    >
      <div className="flex justify-between">
        <span>sleep</span>
        <span className="text-on-surface">{seconds}s</span>
      </div>
    </BaseNode>
  )
}
