import { useState } from 'react'
import { ApiError } from '@/api/client'
import { useCreateTeam, useJoinTeam } from '@/hooks/useTeams'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

/**
 * Join-via-code / create-a-team radio-card picker — shared by the "Teams"
 * tab's "Create / join" route and the demo's team section.
 */
export function TeamJoinCreatePanel({
  onSuccess,
}: {
  // The routed app navigates to `/team/<invite_code>`; the demo tracks the
  // team by `id`. Hand back both so each caller picks what it needs.
  onSuccess?: (team: { id: string; invite_code: string }) => void
}) {
  const [activeCard, setActiveCard] = useState<'join' | 'create' | null>(null)
  const [joinCode, setJoinCode] = useState('')
  const [teamName, setTeamName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const joinTeam = useJoinTeam()
  const createTeam = useCreateTeam()

  function selectCard(card: 'join' | 'create') {
    setActiveCard(card)
    setError(null)
  }

  async function handleJoin() {
    if (!joinCode.trim()) return
    try {
      const team = await joinTeam.mutateAsync(joinCode.trim())
      setError(null)
      onSuccess?.(team)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'An error occurred.')
    }
  }

  async function handleCreate() {
    if (!teamName.trim()) return
    try {
      const team = await createTeam.mutateAsync(teamName.trim())
      setError(null)
      onSuccess?.(team)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'An error occurred.')
    }
  }

  return (
    <div className="flex flex-col gap-3.5">
      <div className="grid grid-cols-2 gap-3">
        <RadioCard
          label="Join a team"
          selected={activeCard === 'join'}
          onClick={() => {
            selectCard('join')
          }}
        />
        <RadioCard
          label="Create a team"
          selected={activeCard === 'create'}
          onClick={() => {
            selectCard('create')
          }}
        />
      </div>

      {activeCard === 'join' && (
        <div className="flex flex-col gap-1.5">
          <Input
            aria-label="Invite code"
            placeholder="e.g. ABCD-1234"
            value={joinCode}
            onChange={(event) => {
              setJoinCode(event.target.value)
            }}
          />
          <Button
            type="button"
            disabled={joinTeam.isPending || !joinCode.trim()}
            onClick={() => {
              void handleJoin()
            }}
          >
            Join
          </Button>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}

      {activeCard === 'create' && (
        <div className="flex flex-col gap-1.5">
          <Input
            aria-label="Team name"
            placeholder="Team name"
            value={teamName}
            onChange={(event) => {
              setTeamName(event.target.value)
            }}
          />
          <Button
            type="button"
            disabled={createTeam.isPending || !teamName.trim()}
            onClick={() => {
              void handleCreate()
            }}
          >
            Create
          </Button>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}
    </div>
  )
}

function RadioCard({
  label,
  selected,
  onClick,
}: {
  label: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        'rounded-(--radius-input) border px-3 py-2.5 text-left text-sm font-semibold transition-colors',
        selected
          ? 'border-accent bg-accent/8 text-foreground'
          : 'border-border text-foreground hover:border-accent/50',
      )}
    >
      {label}
    </button>
  )
}
