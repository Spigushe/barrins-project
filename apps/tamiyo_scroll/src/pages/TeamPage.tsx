import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useCurrentUser } from '@barrins/goblin-guide'
import {
  useDeleteTeam,
  useDownloadTeamDeckReport,
  useEnableTeamDeckThread,
  useFlagTeamDeck,
  useLeaveTeam,
  useMemberDecks,
  usePostTeamDeckThreadMessage,
  useRemoveTeamMember,
  useTeam,
  useTeamDeckThreadMessages,
  useTeamDecks,
  useUnflagTeamDeck,
  useUpdateTeamDescription,
} from '@/hooks/useTeams'
import { ApiError } from '@/api/client'
import { formatDateTime, teamDeckReportFilename } from '@/lib/mtg-format'
import type { TeamDeckOwner } from '@/schemas/tamiyoScroll'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

/**
 * Route-level wrapper — pulls `teamId` from the URL and `currentUserId` from
 * the real (token-gated) `useCurrentUser`, then delegates to
 * `TeamPageContent`. Split out so the demo (`DemoTeamsSection`) can render
 * the same content with a locally-selected team id and its fixed demo
 * identity, without either of them touching real routing or auth.
 */
export function TeamPage() {
  const { teamId } = useParams<{ teamId: string }>()
  const { data: currentUser } = useCurrentUser()

  if (!teamId) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">Loading team…</p>
      </Card>
    )
  }

  return <TeamPageContent teamId={teamId} currentUserId={currentUser?.id ?? null} />
}

/**
 * Full team page — member list, the owner's deck-flagging picker,
 * per-deck-name discussion threads, and the leave/delete-team control
 * (`TeamMembershipCard`). Reached from the "Teams" tab.
 */
export function TeamPageContent({
  teamId,
  currentUserId,
}: {
  teamId: string
  currentUserId: string | null
}) {
  const { data: team } = useTeam(teamId)
  const { data: decks } = useTeamDecks(teamId)
  const removeMember = useRemoveTeamMember()
  const [pendingRemove, setPendingRemove] = useState<{
    userId: string
    label: string
  } | null>(null)

  if (!team) {
    return (
      <Card>
        <p className="text-sm text-muted-foreground">Loading team…</p>
      </Card>
    )
  }

  const isOwner = currentUserId === team.owner_id
  const resolvedTeamId: string = team.id

  async function confirmRemoveMember() {
    if (!pendingRemove) return
    await removeMember.mutateAsync({
      teamId: resolvedTeamId,
      userId: pendingRemove.userId,
    })
    setPendingRemove(null)
  }

  return (
    <div className="flex flex-col gap-7">
      <TeamHeaderCard
        teamId={team.id}
        name={team.name}
        description={team.description}
        inviteCode={team.invite_code}
        isOwner={isOwner}
      />

      {isOwner && <FlagDeckCard teamId={team.id} />}

      <Card>
        <CardTitle>Members</CardTitle>
        <Table className="mt-3">
          <TableHeader>
            <TableRow>
              <TableHead>Member</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Tests + matches logged</TableHead>
              <TableHead>Joined</TableHead>
              {isOwner && <TableHead />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {team.members.map((member) => {
              // Since the identity cutover (ADR-20) the roster carries the
              // identity handle + display name only — never the email. A null
              // username means an inactive / removed identity account.
              const memberLabel =
                member.display_name ?? member.username ?? 'Unknown member'
              return (
                <TableRow key={member.user_id}>
                  <TableCell>{memberLabel}</TableCell>
                  <TableCell>
                    <Badge variant={member.is_owner ? 'owner' : 'default'}>
                      {member.is_owner ? 'Owner' : 'Member'}
                    </Badge>
                  </TableCell>
                  <TableCell>{member.activity_count}</TableCell>
                  <TableCell>{formatDateTime(member.joined_at)}</TableCell>
                  {isOwner && (
                    <TableCell>
                      {!member.is_owner && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-6"
                          aria-label={`Remove ${memberLabel}`}
                          onClick={() => {
                            setPendingRemove({
                              userId: member.user_id,
                              label: memberLabel,
                            })
                          }}
                        >
                          ✕
                        </Button>
                      )}
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </Card>

      <Card>
        <CardTitle>Team Decks</CardTitle>
        {(!decks || decks.length === 0) && (
          <p className="mt-3 text-sm text-muted-foreground">
            No deck has been flagged into this team yet
            {isOwner ? ' — use "Flag a deck" above.' : '.'}
          </p>
        )}
        <div className="mt-3 flex flex-col gap-4">
          {decks?.map((deck) => (
            <TeamDeckThread
              key={deck.name_key}
              teamId={team.id}
              isOwner={isOwner}
              deck={deck}
            />
          ))}
        </div>
      </Card>

      <TeamMembershipCard teamId={team.id} teamName={team.name} isOwner={isOwner} />

      <Dialog
        open={pendingRemove !== null}
        onOpenChange={(next) => {
          if (!next) setPendingRemove(null)
        }}
      >
        {pendingRemove && (
          <DialogContent>
            <DialogTitle>Remove {pendingRemove.label}?</DialogTitle>
            <p className="text-sm text-muted-foreground">
              They'll lose access to this team's shared decks and discussion threads.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setPendingRemove(null)
                }}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={removeMember.isPending}
                onClick={() => {
                  void confirmRemoveMember()
                }}
              >
                Remove
              </Button>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  )
}

function FlagDeckCard({ teamId }: { teamId: string }) {
  const { data: memberDecks } = useMemberDecks(teamId)
  const flagDeck = useFlagTeamDeck()
  const unflagDeck = useUnflagTeamDeck()

  const decks = memberDecks ?? []
  if (decks.length === 0) return null

  return (
    <Card>
      <CardTitle>Flag a deck</CardTitle>
      <p className="mt-1 text-xs text-muted-foreground">
        Flagging a deck's name shares it — and every other member's deck with the exact
        same name, present or future — into this team's testing rotation. Owner-only.
      </p>
      <div className="mt-3 flex flex-col gap-2">
        {decks.map((deck) => (
          <div key={deck.id} className="flex items-center justify-between gap-3">
            <span className="text-sm text-foreground">
              {deck.name}{' '}
              <span className="text-xs text-muted-foreground">
                ({deck.owner_display})
              </span>
            </span>
            <Switch
              checked={deck.is_flagged}
              onCheckedChange={(checked) => {
                if (checked) {
                  flagDeck.mutate({ teamId, deckId: deck.id })
                } else {
                  unflagDeck.mutate({ teamId, nameKey: deck.name.trim().toLowerCase() })
                }
              }}
              label={`Flag ${deck.name} into this team`}
            />
          </div>
        ))}
      </div>
    </Card>
  )
}

function TeamHeaderCard({
  teamId,
  name,
  description,
  inviteCode,
  isOwner,
}: {
  teamId: string
  name: string
  description: string | null
  inviteCode: string
  isOwner: boolean
}) {
  const [draftDescription, setDraftDescription] = useState(description ?? '')
  const [copied, setCopied] = useState(false)
  const updateDescription = useUpdateTeamDescription()

  async function copyCode() {
    await navigator.clipboard.writeText(inviteCode)
    setCopied(true)
    setTimeout(() => {
      setCopied(false)
    }, 2000)
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CardTitle>{name}</CardTitle>
          <Badge variant={isOwner ? 'owner' : 'default'}>
            {isOwner ? 'Owner' : 'Member'}
          </Badge>
        </div>
      </div>
      {isOwner ? (
        <div className="mt-3 flex flex-col gap-1.5">
          <Textarea
            aria-label="Team description"
            value={draftDescription}
            onChange={(event) => {
              setDraftDescription(event.target.value)
            }}
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="self-end"
            disabled={updateDescription.isPending}
            onClick={() => {
              updateDescription.mutate({
                teamId,
                description: draftDescription.trim() || null,
              })
            }}
          >
            Save description
          </Button>
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">
          {description ?? 'No description yet.'}
        </p>
      )}

      {isOwner && (
        <div className="mt-3 flex flex-col gap-1.5">
          <div className="flex items-center justify-between gap-3 rounded-lg border border-dashed border-border/70 bg-input-inline px-3.5 py-3">
            <span className="font-mono text-base font-semibold tracking-wider text-foreground">
              {inviteCode}
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
            Share this code with the players you want to invite to this team.
          </p>
        </div>
      )}
    </Card>
  )
}

/**
 * Leave-team (member) / delete-team (owner) control. Delete is a two-step
 * confirm with an invite-code retype (same pattern as archiving a personal
 * deck, S13); leaving is immediate. Both send the viewer back to `/team`
 * afterwards, which resolves to their next team or the create/join panel.
 */
function TeamMembershipCard({
  teamId,
  teamName,
  isOwner,
}: {
  teamId: string
  teamName: string
  isOwner: boolean
}) {
  const navigate = useNavigate()
  const leaveTeam = useLeaveTeam()
  const deleteTeam = useDeleteTeam()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleteCodeInput, setDeleteCodeInput] = useState('')
  const [deleteError, setDeleteError] = useState<string | null>(null)

  function closeDeleteDialog() {
    setDeleteDialogOpen(false)
    setConfirmingDelete(false)
    setDeleteCodeInput('')
    setDeleteError(null)
  }

  async function confirmDelete() {
    try {
      await deleteTeam.mutateAsync({ teamId, inviteCode: deleteCodeInput.trim() })
      closeDeleteDialog()
      navigate('/team')
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'An error occurred.')
    }
  }

  async function handleLeave() {
    await leaveTeam.mutateAsync(teamId)
    navigate('/team')
  }

  return (
    <Card>
      <CardTitle>{isOwner ? 'Delete team' : 'Leave team'}</CardTitle>
      {isOwner ? (
        <>
          <p className="mt-1 text-xs text-muted-foreground">
            Dissolving the team removes it for every member. This can't be undone.
          </p>
          <Button
            type="button"
            variant="outline"
            className="mt-3 self-start text-destructive"
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
            title={`Delete "${teamName}"?`}
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
        <>
          <p className="mt-1 text-xs text-muted-foreground">
            You'll lose access to this team's shared decks and discussion threads.
          </p>
          <Button
            type="button"
            variant="outline"
            className="mt-3 self-start text-destructive"
            disabled={leaveTeam.isPending}
            onClick={() => {
              void handleLeave()
            }}
          >
            Leave team
          </Button>
        </>
      )}
    </Card>
  )
}

function TeamDeckThread({
  teamId,
  isOwner,
  deck,
}: {
  teamId: string
  isOwner: boolean
  deck: {
    name_key: string
    deck_name: string
    owners: TeamDeckOwner[]
    has_thread: boolean
  }
}) {
  const [messageBody, setMessageBody] = useState('')
  const enableThread = useEnableTeamDeckThread()
  const postMessage = usePostTeamDeckThreadMessage()
  const downloadReport = useDownloadTeamDeckReport()
  const { data: messages } = useTeamDeckThreadMessages(
    deck.has_thread ? teamId : null,
    deck.has_thread ? deck.name_key : null,
  )

  async function handleSend() {
    if (!messageBody.trim()) return
    await postMessage.mutateAsync({
      teamId,
      nameKey: deck.name_key,
      body: messageBody.trim(),
    })
    setMessageBody('')
  }

  return (
    <div className="rounded-(--radius-input) border border-border p-3.5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">{deck.deck_name}</p>
          <p className="text-xs text-muted-foreground">
            {deck.owners.length > 0
              ? `Owned by: ${deck.owners.map((owner) => owner.display).join(', ')}`
              : 'No current member owns a matching deck.'}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={downloadReport.isPending || deck.owners.length === 0}
            onClick={() => {
              downloadReport.mutate({
                teamId,
                nameKey: deck.name_key,
                filename: teamDeckReportFilename(deck),
              })
            }}
          >
            {downloadReport.isPending ? 'Generating…' : 'Download report (PDF)'}
          </Button>
          {isOwner && !deck.has_thread && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={enableThread.isPending}
              onClick={() => {
                enableThread.mutate({ teamId, nameKey: deck.name_key })
              }}
            >
              Enable discussion thread
            </Button>
          )}
        </div>
      </div>

      {deck.has_thread && (
        <div className="mt-3 flex flex-col gap-2">
          <div className="flex max-h-56 flex-col gap-2 overflow-y-auto">
            {messages?.map((message) => (
              <div key={message.id} className="text-sm">
                <span className="font-semibold text-foreground">
                  {message.author_display}
                </span>{' '}
                <span className="text-xs text-muted-foreground">
                  {formatDateTime(message.created_at)}
                </span>
                <p className="text-foreground">{message.body}</p>
              </div>
            ))}
            {(messages?.length ?? 0) === 0 && (
              <p className="text-sm text-muted-foreground">No messages yet.</p>
            )}
          </div>
          <div className="flex gap-2">
            <Input
              aria-label={`Message for ${deck.deck_name}`}
              value={messageBody}
              onChange={(event) => {
                setMessageBody(event.target.value)
              }}
            />
            <Button
              type="button"
              size="sm"
              disabled={postMessage.isPending || !messageBody.trim()}
              onClick={() => {
                void handleSend()
              }}
            >
              Send
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
