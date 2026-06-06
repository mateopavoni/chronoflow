import { useCallback, useEffect, useRef, useState } from 'react'
import { wsUrl } from '../api/client'
import type { ExecutionEventOut } from '../types/api'

interface UseRunStreamOptions {
  /** Run the stream only when enabled=true */
  enabled: boolean
}

interface UseRunStreamResult {
  /** Events received so far, ordered by sequence */
  events: ExecutionEventOut[]
  /** WebSocket connection state */
  connected: boolean
  /** Last error, if any */
  error: string | null
}

const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECTS = 5

/**
 * Opens a WebSocket to /api/ws/runs/{runId} and accumulates ExecutionEventOut messages.
 * Reconnects automatically up to MAX_RECONNECTS times on unexpected close.
 * Cleans up the socket on unmount.
 */
export function useRunStream(runId: string, { enabled }: UseRunStreamOptions): UseRunStreamResult {
  const [events, setEvents] = useState<ExecutionEventOut[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const socketRef = useRef<WebSocket | null>(null)
  const reconnectCount = useRef(0)
  const unmounted = useRef(false)

  const connect = useCallback(() => {
    if (!enabled || unmounted.current) return

    const url = wsUrl(`/ws/runs/${runId}`)
    const ws = new WebSocket(url)
    socketRef.current = ws

    ws.onopen = () => {
      if (unmounted.current) return
      setConnected(true)
      setError(null)
      reconnectCount.current = 0
    }

    ws.onmessage = (ev: MessageEvent<string>) => {
      if (unmounted.current) return
      try {
        const msg = JSON.parse(ev.data) as Record<string, unknown>

        // Control frames are not ExecutionEvents: the server sends
        // { type: "run_finished", status } and { error } messages on the same
        // socket. Injecting them as events corrupts the timeline (undefined
        // node_id → crash), so handle them separately and never store them.
        if (typeof msg['error'] === 'string') {
          setError(msg['error'])
          return
        }
        if (msg['type'] === 'run_finished') return

        // Only accept well-formed ExecutionEventOut payloads.
        if (typeof msg['sequence'] !== 'number' || typeof msg['node_id'] !== 'string') return

        const event = msg as unknown as ExecutionEventOut
        setEvents((prev) => {
          // Avoid duplicates by sequence number
          const exists = prev.some((e) => e.sequence === event.sequence && e.node_id === event.node_id)
          if (exists) return prev
          return [...prev, event].sort((a, b) => a.sequence - b.sequence)
        })
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onerror = () => {
      if (unmounted.current) return
      setError('WebSocket connection error')
      setConnected(false)
    }

    ws.onclose = (ev) => {
      if (unmounted.current) return
      setConnected(false)
      // 1000 = normal close (run finished), 1001 = going away.
      // 4xxx = application close codes (e.g. 4004 = run not found): these are
      // intentional and permanent, so reconnecting would just loop forever and
      // spam "WebSocket connection failed" in the console. Only retry on
      // genuine transient drops (e.g. 1006 abnormal closure).
      const isClean = ev.code === 1000 || ev.code === 1001
      const isAppClose = ev.code >= 4000 && ev.code <= 4999
      if (isAppClose && ev.reason) setError(ev.reason)
      if (!isClean && !isAppClose && reconnectCount.current < MAX_RECONNECTS) {
        reconnectCount.current += 1
        setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }
  }, [runId, enabled])

  useEffect(() => {
    unmounted.current = false
    setEvents([])
    setConnected(false)
    setError(null)

    if (enabled) connect()

    return () => {
      unmounted.current = true
      socketRef.current?.close(1000, 'component unmounted')
    }
  }, [runId, enabled, connect])

  return { events, connected, error }
}
