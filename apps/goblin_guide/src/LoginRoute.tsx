import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { LoginScreen, useIdentity } from '@barrins/goblin-guide'
import { SessionBootSplash } from './SessionBootSplash'

/** Only follow a `?next=` that is a same-origin path (not a protocol-relative URL). */
function safeNext(next: string | null): string {
  return next !== null && next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

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
  )
}
