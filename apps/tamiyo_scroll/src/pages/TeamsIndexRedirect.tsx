import { Navigate } from 'react-router-dom'
import { useMyTeams } from '@/hooks/useTeams'

/** `/app/team` with no team selected — lands on the first team, or the
 * create/join panel if the account has none yet. */
export function TeamsIndexRedirect() {
  const { data: myTeams } = useMyTeams()

  if (!myTeams) return null
  return (
    <Navigate to={myTeams[0] ? `/app/team/${myTeams[0].id}` : '/app/team/new'} replace />
  )
}
