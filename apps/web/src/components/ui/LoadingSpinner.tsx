import { Loader2 } from 'lucide-react'
import { cx } from '../../lib/utils'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  label?: string
}

export function LoadingSpinner({ size = 'md', label = 'Loading...' }: LoadingSpinnerProps) {
  const px = { sm: 16, md: 28, lg: 40 }[size]

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8" role="status" aria-label={label}>
      <Loader2 size={px} className="animate-spin text-on-surface-variant" aria-hidden="true" />
      <span className={cx('font-mono uppercase tracking-wide text-on-surface-variant', size === 'sm' ? 'text-[10px]' : 'text-label-xs')}>
        {label}
      </span>
    </div>
  )
}
