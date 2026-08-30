import { useSearchParams } from 'react-router-dom'
import { Shell } from './Shell'

export function ConfirmEmailChangeRoute() {
  const [searchParams] = useSearchParams()

  // Deep link from the email-change confirmation email:
  // `{FRONTEND_BASE_URL}/confirm-email-change?email=<enc>&code=<6 digits>`.
  // This route sits behind RequireAuth — the verify call needs a Bearer
  // token, so an unauthenticated hit is bounced to /login?next=… first.
  return (
    <Shell
      initialEmailChangeCode={searchParams.get('code') ?? ''}
      initialPendingEmail={searchParams.get('email') ?? ''}
    />
  )
}
