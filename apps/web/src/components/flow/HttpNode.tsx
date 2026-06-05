import type { NodeProps } from '@xyflow/react'
import { BaseNode } from './BaseNode'
import { NODE_META } from './nodeMeta'
import type { HttpConfig } from '../../types/api'

export function HttpNode({ data, selected }: NodeProps) {
  const config = data?.['config'] as HttpConfig | undefined
  const method = config?.method ?? 'GET'
  const url = config?.url ?? ''
  const shortUrl = url.length > 24 ? url.slice(0, 21) + '…' : url

  return (
    <BaseNode
      label={typeof data?.['label'] === 'string' ? data['label'] : 'HTTP'}
      icon={NODE_META.http.icon}
      tag={NODE_META.http.tag}
      selected={selected}
    >
      <div className="flex items-center gap-2">
        <span className="font-semibold text-on-surface">{method}</span>
        <span className="truncate">{shortUrl || '—'}</span>
      </div>
    </BaseNode>
  )
}
