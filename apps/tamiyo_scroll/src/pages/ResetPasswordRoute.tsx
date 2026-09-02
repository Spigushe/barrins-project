import { useNavigate, useSearchParams } from 'react-router-dom'
import { ResetPasswordScreen } from '@barrins/goblin-guide'

export function ResetPasswordRoute() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Deep link from the reset email:
  // `{FRONTEND_BASE_URL}/reset-password?email=<enc>&code=<6 digits>`.
  return (
    <ResetPasswordScreen
      initialEmail={searchParams.get('email') ?? ''}
      initialCode={searchParams.get('code') ?? ''}
      onAuthenticated={() => {
        navigate('/app/metagame', { replace: true })
      }}
      onBackToLogin={() => {
        navigate('/login')
      }}
    />
  )
}
