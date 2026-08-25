import { useState } from 'react'
import { useMyTeams } from '@/hooks/useTeams'
import { Card, CardTitle } from '@/components/ui/card'
import { TeamJoinCreatePanel } from '@/components/layout/TeamJoinCreatePanel'
import { TeamPageContent } from '@/pages/TeamPage'
import { cn } from '@/lib/utils'
import { DEMO_CURRENT_USER_ID } from './demoStore'

const NEW_TEAM = 'new' as const

/**
 * Demo-only "Teams" tab shell. `TeamsTab`/`TeamPage`/`TeamCreateJoinPage`
 * (the real app's equivalents) navigate via `/team/*` routes wrapped in
 * `ProtectedRoute` — reusing them as-is inside `/demo` would bounce an
 * unauthenticated visitor to `/login` the moment they clicked a team (the
 * exact "click a tab, it flashes, then I'm on the login page" bug this
 * component exists to avoid). So this reimplements the same composition
 * with local `useState` instead of routing — the same pattern `DemoPage`
 * already uses for its top-level tabs — while still reusing
 * `TeamJoinCreatePanel` (already prop-driven) and `TeamPageContent`
 * (extracted from `TeamPage` for exactly this purpose) unmodified.
 */
export function DemoTeamsSection() {
  const { data: myTeams } = useMyTeams()
  const [selected, setSelected] = useState<string | typeof NEW_TEAM | null>(null)

  const activeTeamId = selected ?? myTeams?.[0]?.id ?? (myTeams ? NEW_TEAM : null)

  if (activeTeamId === null) return null

  return (
    <div className="flex flex-col gap-5">
      <nav className="flex flex-wrap items-center gap-1 border-b border-border">
        {myTeams?.map((team) => (
          <button
            key={team.id}
            type="button"
            onClick={() => {
              setSelected(team.id)
            }}
            className={cn(
              '-mb-px rounded-t-(--radius-input) border-b-2 border-transparent px-3.5 py-2 text-sm font-semibold text-muted-foreground transition-colors',
              'hover:text-foreground',
              activeTeamId === team.id && 'border-accent bg-card text-foreground',
            )}
          >
            {team.name}
          </button>
        ))}
        <button
          type="button"
          onClick={() => {
            setSelected(NEW_TEAM)
          }}
          className={cn(
            '-mb-px rounded-t-(--radius-input) border-b-2 border-transparent px-3.5 py-2 text-sm font-semibold text-muted-foreground transition-colors',
            'hover:text-foreground',
            activeTeamId === NEW_TEAM && 'border-accent bg-card text-foreground',
          )}
        >
          + Create / join
        </button>
      </nav>

      {activeTeamId === NEW_TEAM ? (
        <Card>
          <CardTitle>Create or join a team</CardTitle>
          <div className="mt-4 max-w-sm">
            <TeamJoinCreatePanel
              onSuccess={(teamId) => {
                setSelected(teamId)
              }}
            />
          </div>
        </Card>
      ) : (
        <TeamPageContent teamId={activeTeamId} currentUserId={DEMO_CURRENT_USER_ID} />
      )}
    </div>
  )
}
