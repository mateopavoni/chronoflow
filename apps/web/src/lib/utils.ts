/** Format an ISO date string to a human-readable local date+time */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

/** Format duration in ms to a readable string */
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

/** Generate a simple UUID-like string for new node IDs */
export function generateId(): string {
  return crypto.randomUUID()
}

/** Attempt to parse a JSON string; return the value or null on failure */
export function tryParseJson(raw: string): Record<string, unknown> | null {
  try {
    return JSON.parse(raw) as Record<string, unknown>
  } catch {
    return null
  }
}

/** Deep clone a value using structuredClone */
export function deepClone<T>(value: T): T {
  return structuredClone(value)
}

/** Join class names, filtering falsy values */
export function cx(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}
