import { get, post } from './client'
import type { ExecutionEventOut, RunOut } from '../types/api'

export const runsApi = {
  list: (workflowId?: string): Promise<RunOut[]> =>
    get(`/runs${workflowId ? `?workflow_id=${workflowId}` : ''}`),

  get: (id: string): Promise<RunOut> => get(`/runs/${id}`),

  getEvents: (id: string): Promise<ExecutionEventOut[]> => get(`/runs/${id}/events`),

  replay: (id: string): Promise<RunOut> => post(`/runs/${id}/replay`),
}
