import { NavLink, Outlet } from 'react-router-dom'
import { useMyTeams } from '@/hooks/useTeams'
import { cn } from '@/lib/utils'

/**
 * "Teams" tab shell — a team can belong to several teams (S2's multi-team
 * decision, 2026-07-30), so this is a sub-tab strip (one per team + a
 * "Create / join" tab), not a single-team page. Body renders via nested
 * routes (`TeamJoinCreatePanel` at `/team` and `/team/new`,
 * `TeamPage` at `/team/:teamId`) — see `App.tsx`.
 */
export function TeamsTab() {
  const { data: myTeams } = useMyTeams()

  return (
    <div className="flex flex-col gap-5">
      <nav className="flex flex-wrap items-center gap-1 border-b border-border">
        {myTeams?.map((team) => (
          <NavLink
            key={team.id}
            to={`/team/${team.id}`}
            className={({ isActive }) =>
              cn(
                '-mb-px rounded-t-(--radius-input) border-b-2 border-transparent px-3.5 py-2 text-sm font-semibold text-muted-foreground transition-colors',
                'hover:text-foreground',
                isActive && 'border-accent bg-card text-foreground',
              )
            }
          >
            {team.name}
          </NavLink>
        ))}
        <NavLink
          to="/team/new"
          className={({ isActive }) =>
            cn(
              '-mb-px rounded-t-(--radius-input) border-b-2 border-transparent px-3.5 py-2 text-sm font-semibold text-muted-foreground transition-colors',
              'hover:text-foreground',
              isActive && 'border-accent bg-card text-foreground',
            )
          }
        >
          + Create / join
        </NavLink>
      </nav>

      <Outlet />
    </div>
  )
}
