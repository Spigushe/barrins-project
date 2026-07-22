import { useState } from 'react'
import { useActiveDeck } from '@/contexts/active-deck-context'
import { useDeleteMatch, useMatches, useUpdateMatch } from '@/hooks/useMatches'
import { useMetaDecks } from '@/hooks/useMetaDecks'
import { usePersonalDecks } from '@/hooks/usePersonalDecks'
import type { GameResult, Match } from '@/schemas/tamiyoScroll'
import {
  formatDate,
  GAME_RESULT_BORDER_CLASS,
  GAME_RESULT_LABELS,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import {
  draftFromMatch,
  MatchFormFields,
  matchDraftIsValid,
  matchDraftToWrite,
  type MatchDraft,
} from './MatchForm'

/** Résultat de match dérivé de la majorité des manches — affichage seul (badge/bordure), pas un calcul métier persisté. */
function matchOutcome(match: Match): GameResult | null {
  const games = [match.game1, match.game2, match.game3].filter(
    (game): game is GameResult => game !== null,
  )
  const wins = games.filter((game) => game === 'win').length
  const losses = games.filter((game) => game === 'loss').length
  if (wins >= 2) return 'win'
  if (losses >= 2) return 'loss'
  if (games.length === 0) return null
  return 'draw'
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

export function MatchJournalSection() {
  const { canEdit } = useActiveDeck()
  const { data: matches } = useMatches()
  const { data: personalDecks } = usePersonalDecks()
  const { data: metaDecks } = useMetaDecks()
  const updateMatch = useUpdateMatch()
  const deleteMatch = useDeleteMatch()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<MatchDraft | null>(null)

  function personalDeckName(id: string) {
    return personalDecks?.find((deck) => deck.id === id)?.name ?? '?'
  }
  function opponentDeckName(id: string) {
    return metaDecks?.find((deck) => deck.id === id)?.name ?? '?'
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
      <CardTitle>Journal des parties</CardTitle>
      <div className="mt-3 flex flex-col gap-3">
        {matches?.map((match) => {
          if (editingId === match.id && editDraft) {
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
                />
                <div className="mt-4 flex gap-2">
                  <Button
                    type="button"
                    disabled={!matchDraftIsValid(editDraft) || updateMatch.isPending}
                    onClick={() => {
                      void handleSaveEdit(match.id)
                    }}
                  >
                    Enregistrer
                  </Button>
                  <Button type="button" variant="outline" onClick={cancelEdit}>
                    Annuler
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
              </div>
              {canEdit && (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      startEdit(match)
                    }}
                  >
                    Éditer
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      void deleteMatch.mutateAsync(match.id)
                    }}
                  >
                    Supprimer
                  </Button>
                </div>
              )}
            </div>
          )
        })}
        {(matches?.length ?? 0) === 0 && (
          <p className="text-center text-muted-foreground">Aucune partie enregistrée.</p>
        )}
      </div>
    </Card>
  )
}
