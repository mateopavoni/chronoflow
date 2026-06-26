import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Workflow } from 'lucide-react'
import { useLogin, useRegister } from '../hooks/useAuth'
import { ErrorBanner } from '../components/ui/ErrorBanner'

interface AuthProps {
  mode: 'login' | 'register'
}

/** Login / register form. Both modes share the markup; the mutation differs. */
export function Auth({ mode }: AuthProps) {
  const navigate = useNavigate()
  const login = useLogin()
  const register = useRegister()
  const mutation = mode === 'login' ? login : register

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const isLogin = mode === 'login'
  const title = isLogin ? 'Sign in' : 'Create account'

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      await mutation.mutateAsync({ email, password })
      navigate('/app')
    } catch {
      // Error is shown via mutation.isError below; catch avoids an unhandled rejection.
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-container-margin">
      <Link to="/" className="mb-8 flex items-center gap-2 text-on-surface">
        <Workflow size={18} className="text-on-surface-variant" aria-hidden="true" />
        <span className="font-mono text-code-sm font-bold uppercase tracking-wider">ChronoFlow</span>
      </Link>

      <form
        onSubmit={(e) => void handleSubmit(e)}
        className="w-full max-w-sm border border-outline-variant bg-surface p-6"
      >
        <h1 className="mb-6 text-headline-md">{title}</h1>

        {mutation.isError && (
          <div className="mb-4">
            <ErrorBanner message={mutation.error?.message ?? 'Something went wrong'} />
          </div>
        )}

        <label className="mb-1 block font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">
          Email
        </label>
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 w-full border border-outline-variant bg-background px-3 py-2 text-body-sm text-on-surface outline-none focus:border-primary"
        />

        <label className="mb-1 block font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">
          Password
        </label>
        <input
          type="password"
          required
          minLength={isLogin ? undefined : 8}
          autoComplete={isLogin ? 'current-password' : 'new-password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-6 w-full border border-outline-variant bg-background px-3 py-2 text-body-sm text-on-surface outline-none focus:border-primary"
        />

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full border border-primary bg-primary px-4 py-2 font-mono text-code-sm font-bold uppercase tracking-wide text-on-primary transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {mutation.isPending ? 'Please wait...' : title}
        </button>

        <p className="mt-4 text-center text-body-sm text-on-surface-variant">
          {isLogin ? (
            <>
              No account?{' '}
              <Link to="/register" className="text-primary hover:underline">
                Create one
              </Link>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </>
          )}
        </p>
      </form>
    </div>
  )
}
