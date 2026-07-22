import { useEffect, useState } from 'react'
import { useActiveDeck } from '@/contexts/active-deck-context'
import { useCreateMatch } from '@/hooks/useMatches'
import { useMetaDecks } from '@/hooks/useMetaDecks'
import { usePersonalDecks } from '@/hooks/usePersonalDecks'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
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
    setDraft((current) =>
      current.personalDeckId === ''
        ? { ...current, personalDeckId: activeDeckId }
        : current,
    )
  }, [activeDeckId])

  if (!canEdit) return null

  async function handleSubmit() {
    if (!matchDraftIsValid(draft)) return
    await createMatch.mutateAsync(matchDraftToWrite(draft))
    setDraft(emptyMatchDraft(activeDeckId))
  }

  return (
    <Card>
      <CardTitle>Nouvelle partie (BO3)</CardTitle>
      <div className="mt-3">
        <MatchFormFields
          draft={draft}
          onChange={setDraft}
          personalDeckOptions={personalDecks ?? []}
          metaDeckOptions={metaDecks ?? []}
        />
        <Button
          type="button"
          className="mt-4"
          disabled={!matchDraftIsValid(draft) || createMatch.isPending}
          onClick={() => {
            void handleSubmit()
          }}
        >
          Enregistrer la partie
        </Button>
      </div>
    </Card>
  )
}
