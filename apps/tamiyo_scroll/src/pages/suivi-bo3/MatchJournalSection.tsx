import { useState } from 'react'
import { useActiveDeck } from '@/contexts/active-deck-context'
import { useDecklistVersions } from '@/hooks/useDecklistVersions'
import { useDeleteMatch, useMatches, useUpdateMatch } from '@/hooks/useMatches'
import { resolveMetaDeckOption, useMetaDecks } from '@/hooks/useMetaDecks'
import { usePersonalDecks } from '@/hooks/usePersonalDecks'
import { useSessions } from '@/hooks/useSessions'
import type {
  GameResult,
  Match,
  MatchGame,
  MatchGameEvent,
  Session,
} from '@/schemas/tamiyoScroll'
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

/** This match's games, always in `game_number` order regardless of the
 * (unordered, "one entry per game actually played") array the backend
 * returns — every reader below assumes ascending order. */
function orderedGames(match: Match) {
  return [...match.games].sort((a, b) => a.game_number - b.game_number)
}

/** Match outcome derived from the majority of games — display only (badge/border), not a persisted business calculation. */
function matchOutcome(match: Match): GameResult | null {
  const results = orderedGames(match)
    .map((game) => game.result)
    .filter((result): result is GameResult => result !== null)
  const wins = results.filter((result) => result === 'win').length
  const losses = results.filter((result) => result === 'loss').length

  // Matches can be closed in only one game, e.g. 1-0 or 0-1, so we need to handle that case as well.
  if (wins > losses) return 'win'
  if (losses > wins) return 'loss'
  if (wins === losses && results.length > 0) return 'draw'

  // If there are no games, we return null to indicate that the outcome is unknown.
  return null
}

function gamesSummary(match: Match): string {
  const byNumber = new Map(match.games.map((game) => [game.game_number, game]))
  return [1, 2, 3]
    .map((gameNumber) => {
      const result = byNumber.get(gameNumber)?.result
      return result ? GAME_RESULT_LABELS[result][0] : '—'
    })
    .join(' / ')
}

function gameByNumber(match: Match, gameNumber: number): MatchGame | undefined {
  return match.games.find((game) => game.game_number === gameNumber)
}

/** One kind's (mulligan/misplay) logged events for one side, read-only —
 * each event gets its own numbered line with its own comment (D2's second
 * amendment: per-event, not per-game×side, comments). The D2 gated data,
 * once it exists, is shown to any viewer the same way the rest of a
 * match's history is (no re-gating a read of already-saved data; only
 * *entering* it is role-gated, in `MatchFormFields`). */
function GameEventList({
  itemLabel,
  events,
}: {
  itemLabel: string
  events: MatchGameEvent[]
}) {
  if (events.length === 0) return null
  return (
    <ol className="flex flex-col">
      {events.map((event, index) => (
        <li key={event.id} className="text-[12.5px] text-muted-foreground">
          <span className="font-semibold text-foreground">
            {itemLabel} #{index + 1}:
          </span>{' '}
          {event.comment || '—'}
        </li>
      ))}
    </ol>
  )
}

/** One side's mulligan/misplay event lists, read-only. `null` means "not
 * tracked" for this side/kind (a sub-`moderator`'s game, or a pre-migration
 * historical row) — nothing to render, same as an empty list. */
function GameSideDetail({
  sideLabel,
  mulligans,
  misplays,
}: {
  sideLabel: string
  mulligans: MatchGameEvent[] | null
  misplays: MatchGameEvent[] | null
}) {
  const mulliganEvents = mulligans ?? []
  const misplayEvents = misplays ?? []
  if (mulliganEvents.length === 0 && misplayEvents.length === 0) return null
  return (
    <div>
      <p className="text-[12.5px] font-semibold text-foreground">
        {sideLabel} — {mulliganEvents.length} mulligan(s), {misplayEvents.length}{' '}
        misplay(s)
      </p>
      <GameEventList itemLabel="Mulligan" events={mulliganEvents} />
      <GameEventList itemLabel="Misplay" events={misplayEvents} />
    </div>
  )
}

/** A game's on_play/result summary, its unchanged free-text Notes (D3),
 * and — only once actually recorded (D8's lazy rows) — the D2 structured
 * per-event mulligan/misplay data per side. */
function GameDetailSection({
  game,
  notesLabel,
  notes,
}: {
  game: MatchGame | undefined
  notesLabel: string
  notes: string | null
}) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <Label>{notesLabel}</Label>
        {game && (
          <span className="text-[12.5px] text-muted-foreground">
            {game.on_play === null
              ? 'Play/Draw unknown'
              : game.on_play
                ? 'On the Play'
                : 'On the Draw'}{' '}
            · {game.result ? GAME_RESULT_LABELS[game.result] : 'In progress'}
          </span>
        )}
      </div>
      <p className="mt-1 whitespace-pre-wrap text-foreground">{notes || '—'}</p>
      {game && (
        <div className="mt-1 flex flex-col gap-1.5">
          <GameSideDetail
            sideLabel="Player"
            mulligans={game.player_mulligans}
            misplays={game.player_misplays}
          />
          <GameSideDetail
            sideLabel="Opponent"
            mulligans={game.opponent_mulligans}
            misplays={game.opponent_misplays}
          />
        </div>
      )}
    </div>
  )
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
                {gameByNumber(match, 1) && (
                  <span className="text-[12.5px] text-muted-foreground">
                    {gameByNumber(match, 1)?.on_play ? 'OTP' : 'OTD'}
                  </span>
                )}
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
                <span className="font-mono">{gamesSummary(viewingMatch)}</span>
                {viewingMatch.session_id && (
                  <SessionBadge session={sessionById(viewingMatch.session_id)} />
                )}
                {viewingMatch.is_readonly && (
                  <Badge variant="shared">sharer: {viewingMatch.shared_by}</Badge>
                )}
              </div>
              <GameDetailSection
                game={gameByNumber(viewingMatch, 1)}
                notesLabel="Game 1 Notes"
                notes={viewingMatch.opening_hand}
              />
              <GameDetailSection
                game={gameByNumber(viewingMatch, 2)}
                notesLabel="Game 2 Notes"
                notes={viewingMatch.turning_point}
              />
              <GameDetailSection
                game={gameByNumber(viewingMatch, 3)}
                notesLabel="Game 3 Notes"
                notes={viewingMatch.final_turn}
              />
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
