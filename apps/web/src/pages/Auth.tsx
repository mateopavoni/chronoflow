import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Workflow } from 'lucide-react'
import { useGuestLogin, useLogin, useRegister } from '../hooks/useAuth'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { ApiError } from '../api/client'

interface AuthProps {
  mode: 'login' | 'register'
}

/** True when the API told us the typed email doesn't belong to any account.
 *  Purely a field-clearing hint — the message shown to the user is the same
 *  generic one either way (see the login route). */
function shouldClearEmail(err: unknown): boolean {
  if (!(err instanceof ApiError) || err.status !== 401) return false
  const detail = err.detail
  return typeof detail === 'object' && detail !== null && 'clear_email' in detail
    ? (detail as { clear_email?: unknown }).clear_email === true
    : false
}

/** Login / register form. Both modes share the markup; the mutation differs. */
export function Auth({ mode }: AuthProps) {
  const navigate = useNavigate()
  const login = useLogin()
  const register = useRegister()
  const guest = useGuestLogin()
  const mutation = mode === 'login' ? login : register

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const isLogin = mode === 'login'
  const title = isLogin ? 'Sign in' : 'Create account'

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      await mutation.mutateAsync({ email, password })
      navigate('/app')
    } catch (err) {
      // Error is shown via mutation.isError below; catch avoids an unhandled rejection.
      // A failed attempt keeps the email so the user only retypes the password —
      // unless the email itself is the part that was wrong (no such account).
      if (shouldClearEmail(err)) setEmail('')
    }
  }

  async function handleGuest() {
    try {
      await guest.mutateAsync()
      navigate('/app')
    } catch {
      // Error is shown via guest.isError below; catch avoids an unhandled rejection.
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

        <button
          type="button"
          onClick={() => void handleGuest()}
          disabled={guest.isPending}
          className="mb-4 w-full border border-primary bg-background px-4 py-3 font-mono text-code-sm font-bold uppercase tracking-wide text-primary transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {guest.isPending ? 'Preparando demo...' : 'Probar demo con datos de ejemplo'}
        </button>

        {guest.isError && (
          <div className="mb-4">
            <ErrorBanner message={guest.error?.message ?? 'Something went wrong'} />
          </div>
        )}

        <div className="mb-4 flex items-center gap-3 text-label-xs uppercase tracking-wide text-on-surface-variant">
          <div className="h-px flex-1 bg-outline-variant" />
          o con cuenta
          <div className="h-px flex-1 bg-outline-variant" />
        </div>

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
        <div className="relative mb-6">
          <input
            type={showPassword ? 'text' : 'password'}
            required
            minLength={isLogin ? undefined : 8}
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border border-outline-variant bg-background px-3 py-2 pr-10 text-body-sm text-on-surface outline-none focus:border-primary"
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            aria-pressed={showPassword}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-on-surface-variant transition-colors hover:text-on-surface focus:text-on-surface focus:outline-none"
          >
            {showPassword ? (
              <EyeOff size={16} aria-hidden="true" />
            ) : (
              <Eye size={16} aria-hidden="true" />
            )}
          </button>
        </div>

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
