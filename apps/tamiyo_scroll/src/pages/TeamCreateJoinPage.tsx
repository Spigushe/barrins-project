import { useNavigate } from 'react-router-dom'
import { TeamJoinCreatePanel } from '@/components/layout/TeamJoinCreatePanel'
import { Card, CardTitle } from '@/components/ui/card'

export function TeamCreateJoinPage() {
  const navigate = useNavigate()

  return (
    <Card>
      <CardTitle>Create or join a team</CardTitle>
      <div className="mt-4 max-w-sm">
        <TeamJoinCreatePanel
          onSuccess={(teamId) => {
            navigate(`/app/team/${teamId}`)
          }}
        />
      </div>
    </Card>
  )
}
