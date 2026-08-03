import { useEffect, useState } from 'react'
import { useActiveDeck } from '@/contexts/active-deck-context'
import { useCreateMatch } from '@/hooks/useMatches'
import { useMetaDecks } from '@/hooks/useMetaDecks'
import { usePersonalDecks } from '@/hooks/usePersonalDecks'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { personalDeckNeedsSetup, PersonalDeckSetupControl } from '@/components/layout/PersonalDeckSetupControl'
import {
  emptyMatchDraft,
  MatchFormFields,
  matchDraftIsValid,
  matchDraftToWrite,
} from './MatchForm'

export function NewMatchSection() {
  const { canEdit, activeDeckId } = useActiveDeck()
  const { data: personalDecks } = usePersonalDecks()
  const { data: metaDecks } = useMetaDecks()
  const createMatch = useCreateMatch()

  const [draft, setDraft] = useState(() => emptyMatchDraft(activeDeckId))

  useEffect(() => {
    if (activeDeckId === null) return
    setDraft((current) => ({ ...current, personalDeckId: activeDeckId }))
  }, [activeDeckId])

  if (!canEdit) return null

  const selectedDeck = personalDecks?.find((deck) => deck.id === draft.personalDeckId)
  // S10/S11: a deck must have both game and category set before a match can
  // be logged on it — mirrors the backend's `_validate_match_refs` gate
  // (`422 personal_deck_game_required`/`personal_deck_macrotype_required`)
  // proactively, instead of waiting for the write to fail.
  const blockedBySetup = personalDeckNeedsSetup(selectedDeck)

  async function handleSubmit() {
    if (!matchDraftIsValid(draft) || blockedBySetup) return
    await createMatch.mutateAsync(matchDraftToWrite(draft))
    setDraft(emptyMatchDraft(activeDeckId))
  }

  return (
    <Card>
      <CardTitle>New game (BO3)</CardTitle>
      <div className="mt-3">
        <MatchFormFields
          draft={draft}
          onChange={setDraft}
          personalDeckOptions={personalDecks ?? []}
          metaDeckOptions={metaDecks ?? []}
        />
        {selectedDeck && blockedBySetup && (
          <div className="mt-3">
            <PersonalDeckSetupControl deck={selectedDeck} />
          </div>
        )}
        <Button
          type="button"
          className="mt-4"
          disabled={!matchDraftIsValid(draft) || blockedBySetup || createMatch.isPending}
          onClick={() => {
            void handleSubmit()
          }}
        >
          Save the game
        </Button>
      </div>
    </Card>
  )
}
