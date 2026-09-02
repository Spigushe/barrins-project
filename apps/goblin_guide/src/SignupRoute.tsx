import { Navigate, useNavigate } from 'react-router-dom'
import { SignupScreen, useIdentity } from '@barrins/goblin-guide'

export function SignupRoute() {
  const navigate = useNavigate()
  const { isAuthenticated } = useIdentity()

  if (isAuthenticated) return <Navigate to="/" replace />

  return (
    <SignupScreen
      onVerificationRequired={(email) => {
        navigate(`/verify-email?email=${encodeURIComponent(email)}`)
      }}
      onAuthenticated={() => {
        navigate('/', { replace: true })
      }}
      onBackToLogin={() => {
        navigate('/login')
      }}
    />
  )
}
