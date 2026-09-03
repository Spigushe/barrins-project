import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCurrentUser } from '@barrins/goblin-guide'
import { useDeleteTeam, useLeaveTeam, useMyTeams, useTeam } from '@/hooks/useTeams'
import { ApiError } from '@/api/client'
import { TeamJoinCreatePanel } from './TeamJoinCreatePanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Input } from '@/components/ui/input'

/**
 * "Team de test" section — quick mode (create/join/leave/delete only).
 * Full mode (member list, discussion threads, "Team Decks" selector) lives
 * on the dedicated team page, linked from the banner below.
 *
 * Per `docs/project/v2.0.0-bump/z-handoff-params-popup/README.md`: an
 * account can belong to several teams (S2's multi-team decision,
 * 2026-07-30), but this quick view only ever shows the first one — a
 * simplified "primary team" view, not the full picker.
 */
export function AccountSettingsTeamSection({ onClose }: { onClose: () => void }) {
  const { data: myTeams } = useMyTeams()
  const primaryTeamId = myTeams?.[0]?.id ?? null
  const { data: team } = useTeam(primaryTeamId)

  if (primaryTeamId === null) {
    return (
      <div className="flex flex-col gap-3.5 border-t border-border pt-[18px]">
        <p className="text-sm font-bold text-foreground">Test team</p>
        <TeamJoinCreatePanel />
      </div>
    )
  }
  if (!team) {
    return null
  }
  return <TeamBanner team={team} onClose={onClose} />
}

function TeamBanner({
  team,
  onClose,
}: {
  team: { id: string; name: string; invite_code: string; owner_id: string }
  onClose: () => void
}) {
  const { data: currentUser } = useCurrentUser()
  const isOwner = currentUser?.id === team.owner_id
  const [copied, setCopied] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleteCodeInput, setDeleteCodeInput] = useState('')
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const leaveTeam = useLeaveTeam()
  const deleteTeam = useDeleteTeam()

  async function handleLeave() {
    await leaveTeam.mutateAsync(team.id)
  }

  function closeDeleteDialog() {
    setDeleteDialogOpen(false)
    setConfirmingDelete(false)
    setDeleteCodeInput('')
    setDeleteError(null)
  }

  async function confirmDelete() {
    try {
      await deleteTeam.mutateAsync({
        teamId: team.id,
        inviteCode: deleteCodeInput.trim(),
      })
      closeDeleteDialog()
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'An error occurred.')
    }
  }

  async function copyCode() {
    await navigator.clipboard.writeText(team.invite_code)
    setCopied(true)
    setTimeout(() => {
      setCopied(false)
    }, 2000)
  }

  return (
    <div className="flex flex-col gap-3.5 border-t border-border pt-[18px]">
      <div className="flex items-center justify-between gap-3">
        <Link
          to={`/team/${team.id}`}
          onClick={onClose}
          className="text-sm font-bold text-foreground hover:underline"
        >
          {team.name}
        </Link>
        <Badge variant={isOwner ? 'owner' : 'default'}>
          {isOwner ? 'Owner' : 'Member'}
        </Badge>
      </div>

      {isOwner ? (
        <>
          <div className="flex items-center justify-between gap-3 rounded-lg border border-dashed border-border/70 bg-input-inline px-3.5 py-3">
            <span className="font-mono text-base font-semibold tracking-wider text-foreground">
              {team.invite_code}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => void copyCode()}
            >
              {copied ? 'Copied!' : 'Copy'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Share this code with the players you want to invite to your team.
          </p>
          <Button
            type="button"
            variant="outline"
            className="text-destructive"
            onClick={() => {
              setDeleteDialogOpen(true)
            }}
          >
            Delete team
          </Button>

          <ConfirmDialog
            open={deleteDialogOpen}
            onOpenChange={(next) => {
              if (!next) closeDeleteDialog()
            }}
            title={`Delete "${team.name}"?`}
            description={
              !confirmingDelete
                ? "This dissolves the team for every member. This can't be undone."
                : 'Type the invite code to confirm.'
            }
            confirmLabel={!confirmingDelete ? 'Continue' : 'Delete permanently'}
            confirmDisabled={
              confirmingDelete && (deleteTeam.isPending || !deleteCodeInput.trim())
            }
            onConfirm={() => {
              if (!confirmingDelete) {
                setConfirmingDelete(true)
                return
              }
              void confirmDelete()
            }}
          >
            {confirmingDelete && (
              <>
                <Input
                  aria-label="Type the invite code to confirm deletion"
                  placeholder="Type the invite code to confirm"
                  value={deleteCodeInput}
                  onChange={(event) => {
                    setDeleteCodeInput(event.target.value)
                  }}
                />
                {deleteError && <p className="text-xs text-destructive">{deleteError}</p>}
              </>
            )}
          </ConfirmDialog>
        </>
      ) : (
        <Button
          type="button"
          variant="outline"
          className="text-destructive"
          disabled={leaveTeam.isPending}
          onClick={() => {
            void handleLeave()
          }}
        >
          Leave team
        </Button>
      )}
    </div>
  )
}
