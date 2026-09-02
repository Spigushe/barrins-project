import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { LoginScreen, useIdentity } from '@barrins/goblin-guide'
import { SessionBootSplash } from '@/components/layout/SessionBootSplash'

/** Only follow a `?next=` that is a same-origin path (not a protocol-relative URL). */
function safeNext(next: string | null): string {
  return next !== null && next.startsWith('/') && !next.startsWith('//')
    ? next
    : '/app/metagame'
}

/**
 * The shared Goblin Guide `<LoginScreen>` (cookie mode), plus Tamiyo's own
 * "Try the demo" entry point (S7) so an unauthenticated visitor can still
 * explore a sample deck without an account.
 */
export function LoginRoute() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isAuthenticated, isBootstrapping } = useIdentity()

  const target = safeNext(searchParams.get('next'))

  // Don't flash the login form while cookie mode is still trying to restore
  // a session from the HttpOnly cookie (ADR-18).
  if (isBootstrapping) return <SessionBootSplash />
  if (isAuthenticated) return <Navigate to={target} replace />

  return (
    <div className="relative">
      <LoginScreen
        sessionExpired={searchParams.get('expired') === '1'}
        accountDeleted={searchParams.get('deleted') === '1'}
        onAuthenticated={() => {
          navigate(target, { replace: true })
        }}
        onForgotPassword={() => {
          navigate('/forgot-password')
        }}
        onCreateAccount={() => {
          navigate('/signup')
        }}
      />
      <p className="pointer-events-none absolute inset-x-0 bottom-6 text-center text-[12.5px] text-muted-foreground">
        Not ready to sign up?{' '}
        <Link
          to="/demo"
          className="pointer-events-auto font-semibold text-accent hover:underline"
        >
          Try the demo
        </Link>
      </p>
    </div>
  )
}
