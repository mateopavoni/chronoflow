import { describe, it, expect, vi, afterEach } from 'vitest'
import { get, post, ApiError, wsUrl } from './client'

// ─── Mock global fetch ────────────────────────────────────────────────────────

function mockFetch(status: number, body: unknown) {
  const response = new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
  vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(response)
}

afterEach(() => {
  vi.restoreAllMocks()
})

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('API client', () => {
  describe('get()', () => {
    it('returns parsed JSON on 200', async () => {
      mockFetch(200, { id: '123', name: 'Test' })
      const result = await get<{ id: string; name: string }>('/workflows')
      expect(result).toEqual({ id: '123', name: 'Test' })
    })

    it('throws ApiError with status and detail on 404', async () => {
      // Mock fetch twice — one call per expect
      mockFetch(404, { detail: 'Workflow not found' })
      mockFetch(404, { detail: 'Workflow not found' })
      await expect(get('/workflows/bad-id')).rejects.toThrow(ApiError)
      await expect(get('/workflows/bad-id')).rejects.toMatchObject({
        status: 404,
        message: 'Workflow not found',
      })
    })

    it('throws ApiError with fallback message when no detail in body', async () => {
      mockFetch(500, {})
      await expect(get('/workflows')).rejects.toThrow(ApiError)
    })
  })

  describe('post()', () => {
    it('sends JSON body and returns parsed response', async () => {
      const payload = { name: 'My WF', graph: { nodes: [], edges: [] } }
      mockFetch(201, { id: 'abc', ...payload })
      const result = await post<{ id: string; name: string }>('/workflows', payload)
      expect(result.id).toBe('abc')
      expect(result.name).toBe('My WF')
    })

    it('throws ApiError on validation error (422)', async () => {
      mockFetch(422, { detail: 'Graph must have a start node' })
      await expect(post('/workflows', {})).rejects.toMatchObject({
        status: 422,
        message: 'Graph must have a start node',
      })
    })

    it('formats structured { message, errors } detail instead of [object Object]', async () => {
      mockFetch(422, {
        detail: {
          message: 'Graph validation failed',
          errors: [
            "The graph must have exactly one 'start' node (found 0).",
            "The graph must have at least one 'end' node (found 0).",
          ],
        },
      })
      await expect(post(`/workflows/x/run`, {})).rejects.toMatchObject({
        status: 422,
        message:
          "Graph validation failed\nThe graph must have exactly one 'start' node (found 0).\nThe graph must have at least one 'end' node (found 0).",
      })
    })

    it('formats Pydantic array detail (loc: msg)', async () => {
      mockFetch(422, {
        detail: [{ loc: ['body', 'trigger_payload'], msg: 'value is not a valid dict', type: 'type_error' }],
      })
      await expect(post('/workflows/x/run', {})).rejects.toMatchObject({
        status: 422,
        message: 'body.trigger_payload: value is not a valid dict',
      })
    })
  })

  describe('wsUrl()', () => {
    it('replaces http with ws', () => {
      // VITE_API_URL is not set in test env; falls back to localhost:8000
      const url = wsUrl('/ws/runs/run-123')
      expect(url).toMatch(/^ws/)
      expect(url).toContain('/api/ws/runs/run-123')
    })
  })
})
