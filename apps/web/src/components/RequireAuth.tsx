import { Navigate, Outlet } from 'react-router-dom'
import { useMe } from '../hooks/useAuth'
import { LoadingSpinner } from './ui/LoadingSpinner'

/** Route guard: renders nested routes only when authenticated, else → /login. */
export function RequireAuth() {
  const { data: user, isLoading } = useMe()
  if (isLoading) return <LoadingSpinner label="Loading..." />
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
