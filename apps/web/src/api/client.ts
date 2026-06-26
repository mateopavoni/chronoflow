// Base API client — wraps fetch with base URL and error handling

const API_BASE = `${import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000'}/api`

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Turn FastAPI's `detail` (which may be a string, our `{message, errors}`
 *  shape, or Pydantic's array of validation errors) into a readable message.
 *  Without this, an object `detail` stringifies to "[object Object]". */
function formatDetail(detail: unknown): string | null {
  if (detail == null) return null
  if (typeof detail === 'string') return detail

  // Our app shape for failed graph validation: { message, errors: string[] }
  if (typeof detail === 'object' && !Array.isArray(detail)) {
    const obj = detail as { message?: unknown; errors?: unknown }
    const parts: string[] = []
    if (typeof obj.message === 'string') parts.push(obj.message)
    if (Array.isArray(obj.errors)) parts.push(...obj.errors.map((e) => String(e)))
    if (parts.length > 0) return parts.join('\n')
  }

  // Pydantic request-validation errors: [{ loc, msg, type }, ...]
  if (Array.isArray(detail)) {
    const msgs = detail.map((e) => {
      if (e && typeof e === 'object' && 'msg' in e) {
        const { loc, msg } = e as { loc?: unknown[]; msg?: unknown }
        const where = Array.isArray(loc) ? loc.join('.') : ''
        return where ? `${where}: ${String(msg)}` : String(msg)
      }
      return String(e)
    })
    if (msgs.length > 0) return msgs.join('\n')
  }

  // Last resort: don't return "[object Object]"
  try {
    return JSON.stringify(detail)
  } catch {
    return null
  }
}

async function parseResponse<T>(res: Response): Promise<T> {
  if (res.status === 204) {
    return undefined as T
  }

  const contentType = res.headers.get('content-type') ?? ''
  const isJson = contentType.includes('application/json')

  if (!res.ok) {
    const body = isJson ? ((await res.json()) as { detail?: unknown }) : null
    const message = formatDetail(body?.detail) ?? `HTTP ${res.status}: ${res.statusText}`
    throw new ApiError(res.status, message)
  }

  return isJson ? ((await res.json()) as T) : (undefined as T)
}

// credentials: 'include' sends the httpOnly session cookie on every request
// (auth lives in the cookie, not in JS). Requires CORS allow_credentials on the API.
export async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'application/json' },
    credentials: 'include',
  })
  return parseResponse<T>(res)
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
  return parseResponse<T>(res)
}

export async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
    credentials: 'include',
  })
  return parseResponse<T>(res)
}

export async function del(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE', credentials: 'include' })
  return parseResponse<void>(res)
}

/** Returns the WebSocket URL corresponding to a REST path.
 *  Replaces http(s) scheme with ws(s) and keeps the /api prefix.
 */
export function wsUrl(path: string): string {
  const base = (import.meta.env['VITE_API_URL'] as string | undefined) ?? 'http://localhost:8000'
  const wsBase = base.replace(/^http/, 'ws')
  return `${wsBase}/api${path}`
}
