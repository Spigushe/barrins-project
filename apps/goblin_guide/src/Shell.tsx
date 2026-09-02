import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { AccountScreen, ApplicationsScreen } from '@barrins/goblin-guide'
import { CURRENT_APP_KEY } from './config'
import { ShellFrame } from './ShellFrame'

export interface ShellProps {
  /** Deep-link `?code=` — opens the account email-change confirmation step. */
  initialEmailChangeCode?: string
  /** Deep-link `?email=` — the pending address, shown in the confirmation banner. */
  initialPendingEmail?: string
}

/**
 * The home page: account management and the role-aware app directory
 * (ADR-19) side by side — two columns on a wide screen, stacked on a
 * narrow one.
 */
const homeGrid: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 460px))',
  gap: 32,
  justifyContent: 'center',
  alignItems: 'start',
  width: '100%',
}

export function Shell({ initialEmailChangeCode, initialPendingEmail }: ShellProps = {}) {
  const navigate = useNavigate()

  return (
    <ShellFrame>
      <div style={homeGrid}>
        <AccountScreen
          initialEmailChangeCode={initialEmailChangeCode}
          initialPendingEmail={initialPendingEmail}
          onDeleted={() => {
            navigate('/login?deleted=1', { replace: true })
          }}
        />
        <ApplicationsScreen currentAppKey={CURRENT_APP_KEY} />
      </div>
    </ShellFrame>
  )
}
