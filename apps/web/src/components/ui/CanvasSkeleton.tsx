import { cx } from '../../lib/utils'

interface CanvasSkeletonProps {
  /** 'editor' mimics the DAG editor chrome; 'debugger' adds the timeline scrubber
   *  bar and inspector panel that the Time-Travel Debugger has instead. */
  variant?: 'editor' | 'debugger'
}

/** Loading placeholder for the React Flow canvas pages (Editor, RunDebugger).
 *
 * Replacing the whole page with a centered spinner (the old behavior) drops the
 * user into a blank screen for as long as the workflow/run fetch takes. This
 * mimics the real layout instead — header bar, dot-matrix canvas with a few
 * pulsing node placeholders shaped like a small DAG, and (for the debugger)
 * the scrubber + inspector chrome — so the page never reads as "broken" or
 * "empty" while data streams in, just "not ready yet".
 */
export function CanvasSkeleton({ variant = 'editor' }: CanvasSkeletonProps) {
  return (
    <div className="flex h-screen flex-col bg-background" role="status" aria-label="Loading workflow canvas">
      {/* Header */}
      <header className="flex shrink-0 items-center gap-3 border-b border-outline-variant bg-surface px-container-margin py-2">
        <div className="h-4 w-20 animate-pulse bg-surface-container-high" />
        <div className="h-5 w-40 animate-pulse bg-surface-container-high" />
        <div className="ml-auto flex items-center gap-2">
          <div className="h-6 w-16 animate-pulse bg-surface-container-high" />
          <div className="h-6 w-16 animate-pulse bg-surface-container-high" />
          <div className="h-6 w-20 animate-pulse bg-surface-container-high" />
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <main className="relative flex-1 dot-matrix">
          <SkeletonNode className="left-[8%] top-[20%]" />
          <SkeletonNode className="left-[42%] top-[45%]" wide />
          <SkeletonNode className="left-[8%] top-[65%]" />
          <SkeletonNode className="left-[74%] top-[45%]" />
        </main>

        {variant === 'debugger' && (
          <aside className="flex w-80 shrink-0 flex-col gap-3 border-l border-outline-variant bg-surface p-4">
            <div className="h-4 w-32 animate-pulse bg-surface-container-high" />
            <div className="h-24 animate-pulse bg-surface-container-high" />
            <div className="h-3 w-full animate-pulse bg-surface-container-high" />
            <div className="h-3 w-2/3 animate-pulse bg-surface-container-high" />
          </aside>
        )}
      </div>

      {variant === 'debugger' && (
        <div className="flex shrink-0 flex-col gap-2 border-t border-outline-variant bg-surface px-container-margin py-3">
          <div className="h-3 w-24 animate-pulse bg-surface-container-high" />
          <div className="flex gap-1">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="h-6 w-6 shrink-0 animate-pulse bg-surface-container-high" />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function SkeletonNode({ className, wide = false }: { className?: string; wide?: boolean }) {
  return (
    <div
      className={cx(
        'absolute h-10 animate-pulse border border-outline-variant bg-surface-container-high',
        wide ? 'w-32' : 'w-24',
        className,
      )}
      aria-hidden="true"
    />
  )
}
