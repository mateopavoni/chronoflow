import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi, type Credentials, type User } from '../api/auth'
import { ApiError } from '../api/client'

export const authKeys = { me: ['auth', 'me'] as const }

/** Current user, or null when not authenticated (401). Other errors propagate. */
export function useMe() {
  return useQuery<User | null>({
    queryKey: authKeys.me,
    queryFn: async () => {
      try {
        return await authApi.me()
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null
        throw err
      }
    },
    staleTime: 60_000,
    retry: false,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (creds: Credentials) => authApi.login(creds),
    onSuccess: (user) => qc.setQueryData(authKeys.me, user),
  })
}

export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (creds: Credentials) => authApi.register(creds),
    onSuccess: (user) => qc.setQueryData(authKeys.me, user),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      qc.setQueryData(authKeys.me, null)
      // Drop any per-user data cached while logged in.
      void qc.invalidateQueries()
    },
  })
}
