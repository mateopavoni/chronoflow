import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { workflowsApi } from '../api/workflows'
import type { WorkflowIn } from '../types/api'

export const workflowKeys = {
  all: ['workflows'] as const,
  detail: (id: string) => ['workflows', id] as const,
}

export function useWorkflows() {
  return useQuery({
    queryKey: workflowKeys.all,
    queryFn: workflowsApi.list,
  })
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: workflowKeys.detail(id),
    queryFn: () => workflowsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateWorkflow() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WorkflowIn) => workflowsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowKeys.all }),
  })
}

export function useUpdateWorkflow(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WorkflowIn) => workflowsApi.update(id, data),
    onSuccess: (updated) => {
      qc.setQueryData(workflowKeys.detail(id), updated)
      void qc.invalidateQueries({ queryKey: workflowKeys.all })
    },
  })
}

export function useDeleteWorkflow() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => workflowsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: workflowKeys.all }),
  })
}

export function useValidateWorkflow() {
  return useMutation({
    mutationFn: (id: string) => workflowsApi.validate(id),
  })
}

export function useRunWorkflow() {
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) =>
      workflowsApi.run(id, payload),
  })
}
