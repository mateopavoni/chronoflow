import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Landing } from './pages/Landing'
import { Auth } from './pages/Auth'
import { Workflows } from './pages/Workflows'
import { Editor } from './pages/Editor'
import { RunDebugger } from './pages/RunDebugger'
import { AppLayout } from './components/ui/AppLayout'
import { RequireAuth } from './components/RequireAuth'

/**
 * React Query client config:
 * - staleTime 30s: reduce refetches for stable data (workflow definitions)
 * - retry 1: fail fast in dev if backend is down
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Auth mode="login" />} />
          <Route path="/register" element={<Auth mode="register" />} />

          {/* Everything under /app requires auth */}
          <Route element={<RequireAuth />}>
            {/* Workflows list — uses the shared app layout with nav */}
            <Route element={<AppLayout />}>
              <Route path="/app" element={<Workflows />} />
            </Route>

            {/* Editor and Debugger — full-screen, own layout */}
            <Route path="/app/workflows/:id" element={<Editor />} />
            <Route path="/app/runs/:id" element={<RunDebugger />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
