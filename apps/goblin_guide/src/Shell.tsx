import { useNavigate } from 'react-router-dom'
import { AccountScreen } from '@barrins/goblin-guide'
import { ShellFrame } from './ShellFrame'

export interface ShellProps {
  /** Deep-link `?code=` — opens the account email-change confirmation step. */
  initialEmailChangeCode?: string
  /** Deep-link `?email=` — the pending address, shown in the confirmation banner. */
  initialPendingEmail?: string
}

export function Shell({ initialEmailChangeCode, initialPendingEmail }: ShellProps = {}) {
  const navigate = useNavigate()

  return (
    <ShellFrame>
      <AccountScreen
        initialEmailChangeCode={initialEmailChangeCode}
        initialPendingEmail={initialPendingEmail}
        onDeleted={() => {
          navigate('/login?deleted=1', { replace: true })
        }}
      />
    </ShellFrame>
  )
}
