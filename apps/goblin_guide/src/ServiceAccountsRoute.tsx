import { useNavigate } from 'react-router-dom'
import { ServiceAccountsScreen } from '@barrins/goblin-guide'
import { ShellFrame } from './ShellFrame'

/**
 * `/service-accounts` — admin service-account management. Behind
 * `RequireAuth` (a logged-out hit bounces to `/login?next=`); the
 * admin-only gate and its access panel live inside `ServiceAccountsScreen`.
 */
export function ServiceAccountsRoute() {
  const navigate = useNavigate()

  return (
    <ShellFrame>
      <ServiceAccountsScreen
        onBack={() => {
          navigate('/')
        }}
      />
    </ShellFrame>
  )
}
