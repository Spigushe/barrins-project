import { ApplicationsScreen } from '@barrins/goblin-guide'
import { CURRENT_APP_KEY } from './config'
import { ShellFrame } from './ShellFrame'

/**
 * `/apps` — the role-aware cross-app launcher (ADR-19). Behind
 * `RequireAuth`; identity computes each app's `access` state, this route
 * just drops Goblin Guide's own card.
 */
export function AppsRoute() {
  return (
    <ShellFrame>
      <ApplicationsScreen currentAppKey={CURRENT_APP_KEY} />
    </ShellFrame>
  )
}
