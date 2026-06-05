import { Inbox, type LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({ icon: Icon = Inbox, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 border border-dashed border-outline-variant bg-surface-dim py-16 text-center">
      <Icon size={32} className="text-on-surface-variant" aria-hidden="true" />
      <h3 className="font-mono text-body-sm uppercase tracking-wide text-on-surface">{title}</h3>
      {description && <p className="max-w-xs text-body-sm text-on-surface-variant">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
