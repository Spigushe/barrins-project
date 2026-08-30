import { useNavigate, useSearchParams } from 'react-router-dom'
import { VerifyEmailScreen } from '@barrins/goblin-guide'

export function VerifyEmailRoute() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Deep link from the verification email:
  // `{FRONTEND_BASE_URL}/verify-email?email=<enc>&code=<6 digits>`.
  return (
    <VerifyEmailScreen
      initialEmail={searchParams.get('email') ?? ''}
      initialCode={searchParams.get('code') ?? ''}
      onAuthenticated={() => {
        navigate('/', { replace: true })
      }}
      onBackToLogin={() => {
        navigate('/login')
      }}
    />
  )
}
