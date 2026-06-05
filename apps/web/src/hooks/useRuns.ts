import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { runsApi } from '../api/runs'

export const runKeys = {
  all: ['runs'] as const,
  byWorkflow: (workflowId: string) => ['runs', 'workflow', workflowId] as const,
  detail: (id: string) => ['runs', id] as const,
  events: (id: string) => ['runs', id, 'events'] as const,
}

export function useRuns(workflowId?: string) {
  return useQuery({
    queryKey: workflowId ? runKeys.byWorkflow(workflowId) : runKeys.all,
    queryFn: () => runsApi.list(workflowId),
  })
}

export function useRun(id: string) {
  const qc = useQueryClient()
  const query = useQuery({
    queryKey: runKeys.detail(id),
    queryFn: () => runsApi.get(id),
    enabled: !!id,
    // Poll every 2s while running; stop when terminal
    refetchInterval: (q) => {
      const data = q.state.data
      if (!data) return 2000
      return data.status === 'running' || data.status === 'pending' ? 2000 : false
    },
  })

  // When a run finishes, invalidate events cache (React Query v5: no onSuccess in useQuery)
  const status = query.data?.status
  useEffect(() => {
    if (status === 'completed' || status === 'failed') {
      void qc.invalidateQueries({ queryKey: runKeys.events(id) })
    }
  }, [status, id, qc])

  return query
}

export function useRunEvents(runId: string) {
  return useQuery({
    queryKey: runKeys.events(runId),
    queryFn: () => runsApi.getEvents(runId),
    enabled: !!runId,
  })
}

export function useReplayRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => runsApi.replay(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: runKeys.all }),
  })
}
