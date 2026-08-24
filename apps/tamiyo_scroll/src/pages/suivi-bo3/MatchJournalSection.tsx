import { useState } from 'react'
import { useActiveDeck } from '@/contexts/active-deck-context'
import { useDecklistVersions } from '@/hooks/useDecklistVersions'
import { useDeleteMatch, useMatches, useUpdateMatch } from '@/hooks/useMatches'
import { resolveMetaDeckOption, useMetaDecks } from '@/hooks/useMetaDecks'
import { usePersonalDecks } from '@/hooks/usePersonalDecks'
import { useSessions } from '@/hooks/useSessions'
import type { GameResult, Match, Session } from '@/schemas/tamiyoScroll'
import {
  formatDate,
  GAME_RESULT_BORDER_CLASS,
  GAME_RESULT_LABELS,
  SESSION_TYPE_LABELS,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  personalDeckNeedsSetup,
  PersonalDeckSetupControl,
} from '@/components/layout/PersonalDeckSetupControl'
import { SessionTypeBadge } from '@/components/session/SessionTypeBadge'
import {
  draftFromMatch,
  MatchFormFields,
  matchDraftIsValid,
  matchDraftToWrite,
  type MatchDraft,
} from './MatchForm'

/** Match outcome derived from the majority of games — display only (badge/border), not a persisted business calculation. */
function matchOutcome(match: Match): GameResult | null {
  const games = [match.game1, match.game2, match.game3].filter(
    (game): game is GameResult => game !== null,
  )
  const wins = games.filter((game) => game === 'win').length
  const losses = games.filter((game) => game === 'loss').length

  // Matches can be closed in only one game, e.g. 1-0 or 0-1, so we need to handle that case as well.
  if (wins > losses) return 'win'
  if (losses > wins) return 'loss'
  if (wins === losses && games.length > 0) return 'draw'

  // If there are no games, we return null to indicate that the outcome is unknown.
  return null
}

function gamesSummary(match: Match): string {
  return [match.game1, match.game2, match.game3]
    .map((game) => (game === null ? '—' : GAME_RESULT_LABELS[game][0]))
    .join(' / ')
}

const OUTCOME_BADGE_VARIANT: Record<GameResult, 'success' | 'destructive' | 'warning'> = {
  win: 'success',
  loss: 'destructive',
  draw: 'warning',
}

/** Session tag, colored by the session's hue (S14) if set, falling back to
 * its type (S9, same mapping as the Sessions tab's
 * `SESSION_TYPE_BADGE_VARIANT`). The session lookup includes archived
 * sessions (S14 auto-archive makes this common now), so a historical
 * match's tag still resolves instead of falling back to "?". */
function SessionBadge({ session }: { session: Session | undefined }) {
  if (!session) return <Badge>?</Badge>
  return (
    <SessionTypeBadge session={session}>
      {SESSION_TYPE_LABELS[session.type]}: {session.name}
    </SessionTypeBadge>
  )
}

export function MatchJournalSection() {
  const { canEdit, activeDeckId } = useActiveDeck()
  const { data: matches } = useMatches(activeDeckId)
  const { data: personalDecks } = usePersonalDecks()
  const { data: metaDecks } = useMetaDecks()
  // A historical match can point at a roster entry the owner has since
  // archived (or, for a shared match, one collapsed away when a same-name
  // own entry appeared later) — the default query excludes archived rows
  // so the edit form's picker never offers them, but resolving *display*
  // names for the journal needs to see them too, to tell "deleted roster
  // entry" apart from a genuinely broken reference.
  const { data: metaDecksIncludingArchived } = useMetaDecks({ includeArchived: true })
  // Include archived sessions (S14 auto-archive makes them common) — same
  // "resolve display data even for a since-archived row" precedent as
  // `metaDecksIncludingArchived` above.
  const { data: sessions } = useSessions(activeDeckId, true)
  const updateMatch = useUpdateMatch()
  const deleteMatch = useDeleteMatch()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<MatchDraft | null>(null)
  const [viewingMatch, setViewingMatch] = useState<Match | null>(null)
  const [pendingDelete, setPendingDelete] = useState<Match | null>(null)
  const { data: editingDeckVersions } = useDecklistVersions(
    editDraft?.personalDeckId ?? null,
  )

  function personalDeckName(id: string) {
    return personalDecks?.find((deck) => deck.id === id)?.name ?? '?'
  }
  function opponentDeckName(id: string) {
    const active = resolveMetaDeckOption(metaDecks, id)
    if (active) return active.name
    const archived = resolveMetaDeckOption(metaDecksIncludingArchived, id)
    if (archived) return 'Deleted deck'
    return '?'
  }
  function sessionById(id: string) {
    return sessions?.find((session) => session.id === id)
  }

  function startEdit(match: Match) {
    setEditingId(match.id)
    setEditDraft(draftFromMatch(match))
  }

  function cancelEdit() {
    setEditingId(null)
    setEditDraft(null)
  }

  async function handleSaveEdit(matchId: string) {
    if (!editDraft || !matchDraftIsValid(editDraft)) return
    await updateMatch.mutateAsync({ matchId, payload: matchDraftToWrite(editDraft) })
    cancelEdit()
  }

  return (
    <Card>
      <CardTitle>Match log</CardTitle>
      <div className="mt-3 flex flex-col gap-3">
        {matches?.map((match) => {
          if (editingId === match.id && editDraft) {
            const editingDeck = personalDecks?.find(
              (deck) => deck.id === editDraft.personalDeckId,
            )
            const blockedBySetup = personalDeckNeedsSetup(editingDeck)
            return (
              <div
                key={match.id}
                className="rounded-(--radius-input) border border-border bg-input-inline p-4"
              >
                <MatchFormFields
                  draft={editDraft}
                  onChange={setEditDraft}
                  personalDeckOptions={personalDecks ?? []}
                  metaDeckOptions={metaDecks ?? []}
                  decklistVersionOptions={editingDeckVersions}
                />
                {editingDeck && blockedBySetup && (
                  <div className="mt-3">
                    <PersonalDeckSetupControl deck={editingDeck} />
                  </div>
                )}
                <div className="mt-4 flex gap-2">
                  <Button
                    type="button"
                    disabled={
                      !matchDraftIsValid(editDraft) ||
                      blockedBySetup ||
                      updateMatch.isPending
                    }
                    onClick={() => {
                      void handleSaveEdit(match.id)
                    }}
                  >
                    Save
                  </Button>
                  <Button type="button" variant="outline" onClick={cancelEdit}>
                    Cancel
                  </Button>
                </div>
              </div>
            )
          }

          const outcome = matchOutcome(match)
          return (
            <div
              key={match.id}
              className={cn(
                'flex flex-wrap items-center justify-between gap-3 rounded-(--radius-input) border border-l-4 border-border bg-input-inline p-3',
                outcome ? GAME_RESULT_BORDER_CLASS[outcome] : 'border-l-border',
              )}
            >
              <div className="flex flex-wrap items-center gap-3">
                {outcome && (
                  <Badge variant={OUTCOME_BADGE_VARIANT[outcome]}>
                    {GAME_RESULT_LABELS[outcome]}
                  </Badge>
                )}
                <span className="text-sm">
                  <span className="text-muted-foreground">
                    {personalDeckName(match.personal_deck_id)}
                  </span>{' '}
                  <span className="text-muted-foreground">vs</span>{' '}
                  <span className="font-semibold text-foreground">
                    {opponentDeckName(match.opponent_deck_id)}
                  </span>
                </span>
                <span className="text-[12.5px] text-muted-foreground">
                  {match.on_play ? 'OTP' : 'OTD'}
                </span>
                <span className="font-mono text-[12.5px] text-muted-foreground">
                  {gamesSummary(match)}
                </span>
                <span className="text-[12.5px] text-subtle-foreground">
                  {formatDate(match.date)}
                </span>
                {match.session_id && (
                  <SessionBadge session={sessionById(match.session_id)} />
                )}
                {match.is_readonly && (
                  <Badge variant="shared">sharer: {match.shared_by}</Badge>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setViewingMatch(match)
                  }}
                >
                  View
                </Button>
                {canEdit && !match.is_readonly && (
                  <>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        startEdit(match)
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setPendingDelete(match)
                      }}
                    >
                      Delete
                    </Button>
                  </>
                )}
              </div>
            </div>
          )
        })}
        {(matches?.length ?? 0) === 0 && (
          <p className="text-center text-muted-foreground">No game saved.</p>
        )}
      </div>

      <Dialog
        open={viewingMatch !== null}
        onOpenChange={(open) => {
          if (!open) setViewingMatch(null)
        }}
      >
        {viewingMatch && (
          <DialogContent>
            <DialogTitle>
              {personalDeckName(viewingMatch.personal_deck_id)} vs{' '}
              {opponentDeckName(viewingMatch.opponent_deck_id)}
            </DialogTitle>
            <div className="flex flex-col gap-3 text-sm">
              <div className="flex flex-wrap items-center gap-3 text-muted-foreground">
                <span>{formatDate(viewingMatch.date)}</span>
                <span>{viewingMatch.on_play ? 'On the Play' : 'On the Draw'}</span>
                <span className="font-mono">{gamesSummary(viewingMatch)}</span>
                {viewingMatch.session_id && (
                  <SessionBadge session={sessionById(viewingMatch.session_id)} />
                )}
                {viewingMatch.is_readonly && (
                  <Badge variant="shared">sharer: {viewingMatch.shared_by}</Badge>
                )}
              </div>
              <div>
                {/* S12 item 3: label-only rename — `opening_hand` unchanged. */}
                <Label>Game 1 Notes</Label>
                <p className="mt-1 whitespace-pre-wrap text-foreground">
                  {viewingMatch.opening_hand || '—'}
                </p>
              </div>
              <div>
                {/* S12 item 3: label-only rename — `turning_point` unchanged. */}
                <Label>Game 2 Notes</Label>
                <p className="mt-1 whitespace-pre-wrap text-foreground">
                  {viewingMatch.turning_point || '—'}
                </p>
              </div>
              <div>
                {/* S12 item 3: label-only rename — `final_turn` unchanged. */}
                <Label>Game 3 Notes</Label>
                <p className="mt-1 whitespace-pre-wrap text-foreground">
                  {viewingMatch.final_turn || '—'}
                </p>
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(next) => {
          if (!next) setPendingDelete(null)
        }}
        title={
          pendingDelete
            ? `Delete ${personalDeckName(pendingDelete.personal_deck_id)} vs ${opponentDeckName(pendingDelete.opponent_deck_id)}?`
            : ''
        }
        description="It will disappear from the match log. This can't be undone."
        confirmDisabled={deleteMatch.isPending}
        onConfirm={() => {
          if (!pendingDelete) return
          void deleteMatch.mutateAsync(pendingDelete.id)
          setPendingDelete(null)
        }}
      />
    </Card>
  )
}
