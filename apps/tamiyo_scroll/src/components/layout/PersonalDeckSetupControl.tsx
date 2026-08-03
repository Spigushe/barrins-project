import { useState } from 'react'
import { useUpdatePersonalDeck } from '@/hooks/usePersonalDecks'
import type { ArchetypeCategory, CardGame, PersonalDeck } from '@/schemas/tamiyoScroll'
import { ARCHETYPE_LABELS, CARD_GAME_LABELS } from '@/lib/mtg-format'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const CARD_GAME_OPTIONS = Object.keys(CARD_GAME_LABELS) as CardGame[]
const ARCHETYPE_OPTIONS = Object.keys(ARCHETYPE_LABELS) as ArchetypeCategory[]

/** True once both S10 (game) and S11 (category) are set — the deck can be
 * used to log or edit a match. Historical, pre-migration decks read both
 * as `null` until fixed via this control's PATCH call. */
export function personalDeckNeedsSetup(deck: PersonalDeck | undefined | null): boolean {
  if (!deck) return false
  return deck.game === null || deck.category === null
}

/**
 * Inline "set game/macrotype before logging results" fix, shared by the
 * deck view (`PersonalDeckSelector`) and the match-logging entry points
 * (`NewMatchSection`, `MatchJournalSection`'s edit flow) — S10/S11's gate
 * on `_validate_match_refs` rejects a match create/edit on a deck missing
 * either field with `422 personal_deck_game_required` /
 * `personal_deck_macrotype_required`; this is how the UI unblocks it
 * without waiting for that error to happen first.
 */
export function PersonalDeckSetupControl({ deck }: { deck: PersonalDeck }) {
  const updateDeck = useUpdatePersonalDeck()
  const [game, setGame] = useState<CardGame | ''>(deck.game ?? '')
  const [category, setCategory] = useState<ArchetypeCategory | ''>(deck.category ?? '')

  if (!personalDeckNeedsSetup(deck)) return null

  const canSave = game !== '' && category !== ''

  async function handleSave() {
    if (!canSave) return
    await updateDeck.mutateAsync({ deckId: deck.id, game, category } as {
      deckId: string
      game: CardGame
      category: ArchetypeCategory
    })
  }

  return (
    <div className="flex flex-wrap items-end gap-2 rounded-(--radius-input) border border-warning/40 bg-warning/10 p-2">
      <p className="w-full text-xs text-muted-foreground">
        Set "{deck.name}"'s game and archetype before logging results.
      </p>
      <div className="flex flex-col gap-1">
        <Label className="text-xs">Game</Label>
        <Select value={game} onValueChange={(v) => { setGame(v as CardGame) }}>
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="— select —" />
          </SelectTrigger>
          <SelectContent>
            {CARD_GAME_OPTIONS.map((option) => (
              <SelectItem key={option} value={option}>
                {CARD_GAME_LABELS[option]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex flex-col gap-1">
        <Label className="text-xs">Archetype</Label>
        <Select value={category} onValueChange={(v) => { setCategory(v as ArchetypeCategory) }}>
          <SelectTrigger className="h-8 w-32 text-xs">
            <SelectValue placeholder="— select —" />
          </SelectTrigger>
          <SelectContent>
            {ARCHETYPE_OPTIONS.map((option) => (
              <SelectItem key={option} value={option}>
                {ARCHETYPE_LABELS[option]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        type="button"
        size="sm"
        disabled={!canSave || updateDeck.isPending}
        onClick={() => {
          void handleSave()
        }}
      >
        Save
      </Button>
    </div>
  )
}
