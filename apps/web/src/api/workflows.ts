import { del, get, post, put } from './client'
import type { ValidationResult, WorkflowIn, WorkflowOut } from '../types/api'

export const workflowsApi = {
  list: (): Promise<WorkflowOut[]> => get('/workflows'),

  get: (id: string): Promise<WorkflowOut> => get(`/workflows/${id}`),

  create: (data: WorkflowIn): Promise<WorkflowOut> => post('/workflows', data),

  update: (id: string, data: WorkflowIn): Promise<WorkflowOut> => put(`/workflows/${id}`, data),

  delete: (id: string): Promise<void> => del(`/workflows/${id}`),

  validate: (id: string): Promise<ValidationResult> => post(`/workflows/${id}/validate`),

  run: (id: string, trigger_payload: Record<string, unknown>) =>
    post<{ id: string; workflow_id: string; status: string }>(`/workflows/${id}/run`, {
      trigger_payload,
    }),
}
