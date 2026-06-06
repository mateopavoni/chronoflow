import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { X } from 'lucide-react'
import { cx } from '../../lib/utils'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg'
}

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open) dialog.showModal()
    else dialog.close()
  }, [open])

  function handleClick(e: React.MouseEvent<HTMLDialogElement>) {
    if (e.target === dialogRef.current) onClose()
  }

  const widthClass = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' }[size]

  return (
    <dialog
      ref={dialogRef}
      onClick={handleClick}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
      className={cx('mx-auto mt-24 w-full bg-transparent p-0', widthClass)}
      aria-labelledby="modal-title"
      aria-modal="true"
    >
      <div className="mx-4 border-2 border-outline-variant bg-surface text-on-surface">
        <div className="flex items-center justify-between border-b border-outline-variant bg-surface-container-lowest px-4 py-3">
          <h2 id="modal-title" className="font-mono text-code-sm font-bold uppercase tracking-wide text-on-surface">
            {title}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="flex h-6 w-6 items-center justify-center text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
          >
            <X size={16} />
          </button>
        </div>
        <div className="px-4 py-4">{children}</div>
      </div>
    </dialog>
  )
}
