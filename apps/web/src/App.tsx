import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Workflows } from './pages/Workflows'
import { Editor } from './pages/Editor'
import { RunDebugger } from './pages/RunDebugger'
import { AppLayout } from './components/ui/AppLayout'

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
          {/* Workflows list — uses the shared app layout with nav */}
          <Route element={<AppLayout />}>
            <Route path="/" element={<Workflows />} />
          </Route>

          {/* Editor and Debugger — full-screen, own layout */}
          <Route path="/workflows/:id" element={<Editor />} />
          <Route path="/runs/:id" element={<RunDebugger />} />
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
