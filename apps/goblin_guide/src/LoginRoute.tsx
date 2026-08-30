import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { LoginScreen, useIdentity } from '@barrins/goblin-guide'

export function LoginRoute() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useIdentity()

  if (isAuthenticated) return <Navigate to="/" replace />

  return (
    <LoginScreen
      sessionExpired={searchParams.get('expired') === '1'}
      onAuthenticated={() => {
        navigate('/', { replace: true })
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
