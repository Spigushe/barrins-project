import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { ForgotPasswordScreen, useIdentity } from '@barrins/goblin-guide'

export function ForgotPasswordRoute() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useIdentity()

  if (isAuthenticated) return <Navigate to="/app/metagame" replace />

  return (
    <ForgotPasswordScreen
      initialEmail={searchParams.get('email') ?? ''}
      onEnterCode={(email) => {
        navigate(
          email === ''
            ? '/reset-password'
            : `/reset-password?email=${encodeURIComponent(email)}`,
        )
      }}
      onBackToLogin={() => {
        navigate('/login')
      }}
    />
  )
}
