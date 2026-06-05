interface JsonViewerProps {
  data: unknown
  label?: string
}

/**
 * Renders a JSON payload as a line-numbered monospace block (console inspector).
 * Used in the run debugger inspector panel.
 */
export function JsonViewer({ data, label }: JsonViewerProps) {
  if (data === undefined || data === null) {
    return <span className="font-mono text-label-xs text-on-surface-variant">—</span>
  }

  const lines = JSON.stringify(data, null, 2).split('\n')

  return (
    <div>
      {label && (
        <p className="mb-1 font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">{label}</p>
      )}
      <div className="max-h-60 overflow-auto border border-outline-variant bg-surface-container-lowest">
        <pre className="font-mono text-code-sm leading-relaxed text-on-surface">
          {lines.map((line, i) => (
            <div key={i} className="flex hover:bg-surface-container">
              <span className="w-9 shrink-0 select-none border-r border-outline-variant px-2 text-right text-on-surface-variant/60">
                {i + 1}
              </span>
              <span className="whitespace-pre px-2">{line}</span>
            </div>
          ))}
        </pre>
      </div>
    </div>
  )
}
