import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { LoginScreen, useIdentity } from '@barrins/goblin-guide'

/** Only follow a `?next=` that is a same-origin path (not a protocol-relative URL). */
function safeNext(next: string | null): string {
  return next !== null && next.startsWith('/') && !next.startsWith('//') ? next : '/'
}

export function LoginRoute() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useIdentity()

  const target = safeNext(searchParams.get('next'))

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
