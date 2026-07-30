import { type FormEvent, useState } from 'react'
import { useCreateMetaDeck } from '@/hooks/useMetaDecks'
import type { ArchetypeCategory, Match, MatchWrite } from '@/schemas/tamiyoScroll'
import { ARCHETYPE_LABELS, GAME_RESULT_LABELS } from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

export const GAME_NOT_PLAYED = '__not_played__'
const GAME_OPTIONS = ['win', 'loss', 'draw'] as const
const TIERS = [0, 0.5, 1, 1.5, 2, 2.5, 3]
const ARCHETYPE_OPTIONS = Object.keys(ARCHETYPE_LABELS) as ArchetypeCategory[]
const CREATE_ITEM_VALUE = 'create-new-opponent-deck'

export interface MatchDraft {
  personalDeckId: string
  opponentDeckId: string
  decklistVersionId: string | null
  onPlay: boolean
  game1: string
  game2: string
  game3: string
  openingHand: string
  turningPoint: string
  finalTurn: string
}

export function emptyMatchDraft(defaultPersonalDeckId: string | null): MatchDraft {
  return {
    personalDeckId: defaultPersonalDeckId ?? '',
    opponentDeckId: '',
    decklistVersionId: null,
    onPlay: true,
    game1: GAME_NOT_PLAYED,
    game2: GAME_NOT_PLAYED,
    game3: GAME_NOT_PLAYED,
    openingHand: '',
    turningPoint: '',
    finalTurn: '',
  }
}

export function draftFromMatch(match: Match): MatchDraft {
  return {
    personalDeckId: match.personal_deck_id,
    opponentDeckId: match.opponent_deck_id,
    decklistVersionId: match.decklist_version_id,
    onPlay: match.on_play,
    game1: match.game1 ?? GAME_NOT_PLAYED,
    game2: match.game2 ?? GAME_NOT_PLAYED,
    game3: match.game3 ?? GAME_NOT_PLAYED,
    openingHand: match.opening_hand ?? '',
    turningPoint: match.turning_point ?? '',
    finalTurn: match.final_turn ?? '',
  }
}

export function matchDraftToWrite(draft: MatchDraft): MatchWrite {
  return {
    personal_deck_id: draft.personalDeckId,
    opponent_deck_id: draft.opponentDeckId,
    decklist_version_id: draft.decklistVersionId,
    on_play: draft.onPlay,
    game1: draft.game1 === GAME_NOT_PLAYED ? null : (draft.game1 as MatchWrite['game1']),
    game2: draft.game2 === GAME_NOT_PLAYED ? null : (draft.game2 as MatchWrite['game2']),
    game3: draft.game3 === GAME_NOT_PLAYED ? null : (draft.game3 as MatchWrite['game3']),
    opening_hand: draft.openingHand.trim() || null,
    turning_point: draft.turningPoint.trim() || null,
    final_turn: draft.finalTurn.trim() || null,
  }
}

export function matchDraftIsValid(draft: MatchDraft): boolean {
  return draft.personalDeckId !== '' && draft.opponentDeckId !== ''
}

function GameResultSelect({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={GAME_NOT_PLAYED}>— not played —</SelectItem>
          {GAME_OPTIONS.map((result) => (
            <SelectItem key={result} value={result}>
              {GAME_RESULT_LABELS[result]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

/**
 * Opponent deck field: search existing meta decks, or type a new name and
 * "Create" it without leaving this form. name/tier/category match exactly
 * what the existing quick-add form on the Metagame roster page collects
 * (`MetaDecksSections.tsx`) — top8/presence/expected default the same way
 * it does (0/0/'as_expected': a freshly-noted deck genuinely has zero
 * recorded Top 8s/presence so far, and hasn't been evaluated against
 * expectations yet).
 */
function OpponentDeckField({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (deckId: string) => void
  options: { id: string; name: string }[]
}) {
  const createMetaDeck = useCreateMetaDeck()

  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [creating, setCreating] = useState(false)
  const [pendingName, setPendingName] = useState('')
  const [newTier, setNewTier] = useState(1)
  const [newCategory, setNewCategory] = useState<ArchetypeCategory>('midrange')

  const selected = options.find((deck) => deck.id === value)
  const trimmedSearch = search.trim()
  const filtered = options.filter((deck) =>
    deck.name.toLowerCase().includes(trimmedSearch.toLowerCase()),
  )
  const hasExactMatch = options.some(
    (deck) => deck.name.toLowerCase() === trimmedSearch.toLowerCase(),
  )

  function selectDeck(deckId: string) {
    onChange(deckId)
    setOpen(false)
    setSearch('')
  }

  function openCreateDialog() {
    setPendingName(trimmedSearch)
    setCreating(true)
    setOpen(false)
    setSearch('')
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    const created = await createMetaDeck.mutateAsync({
      name: pendingName,
      tier: newTier,
      category: newCategory,
      decklist_notes: null,
      top8: 0,
      presence: 0,
      expected: 'as_expected',
      tests_status: null,
    })
    onChange(created.id)
    setCreating(false)
    setNewTier(1)
    setNewCategory('midrange')
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Label id="opponent-deck-label">Opponent</Label>
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (!next) setSearch('')
        }}
      >
        <PopoverTrigger
          aria-labelledby="opponent-deck-label"
          className={cn(
            'flex h-9 w-52 items-center justify-between gap-2 rounded-(--radius-input) border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors',
            'focus-visible:border-accent',
          )}
        >
          <span className="min-w-0 flex-1 truncate text-left">
            {selected?.name ?? '— select —'}
          </span>
        </PopoverTrigger>
        <PopoverContent className="p-0">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search or create…"
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              {filtered.length === 0 && !trimmedSearch && (
                <CommandEmpty>No opponent decks yet.</CommandEmpty>
              )}
              <CommandGroup>
                {filtered.map((deck) => (
                  <CommandItem
                    key={deck.id}
                    value={deck.id}
                    onSelect={() => {
                      selectDeck(deck.id)
                    }}
                  >
                    {deck.id === value ? '✓ ' : ''}
                    {deck.name}
                  </CommandItem>
                ))}
                {trimmedSearch && !hasExactMatch && (
                  <CommandItem
                    value={CREATE_ITEM_VALUE}
                    onSelect={() => {
                      openCreateDialog()
                    }}
                  >
                    Create "{trimmedSearch}"
                  </CommandItem>
                )}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent>
          <DialogTitle>Create opponent deck</DialogTitle>
          <form
            className="flex flex-col gap-3"
            onSubmit={(event) => {
              void handleCreate(event)
            }}
          >
            <div>
              <Label>Name</Label>
              <p className="mt-1 text-sm font-medium text-foreground">{pendingName}</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <div className="flex flex-col gap-1.5">
                <Label>Tier</Label>
                <Select
                  value={String(newTier)}
                  onValueChange={(v) => {
                    setNewTier(Number(v))
                  }}
                >
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIERS.map((tier) => (
                      <SelectItem key={tier} value={String(tier)}>
                        {tier}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Category</Label>
                <Select
                  value={newCategory}
                  onValueChange={(v) => {
                    setNewCategory(v as ArchetypeCategory)
                  }}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ARCHETYPE_OPTIONS.map((category) => (
                      <SelectItem key={category} value={category}>
                        {ARCHETYPE_LABELS[category]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={createMetaDeck.isPending}>
                Create
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setCreating(false)
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

const NO_VERSION_VALUE = '__no_version__'

export function MatchFormFields({
  draft,
  onChange,
  personalDeckOptions,
  metaDeckOptions,
  decklistVersionOptions,
}: {
  draft: MatchDraft
  onChange: (next: MatchDraft) => void
  personalDeckOptions: { id: string; name: string }[]
  metaDeckOptions: { id: string; name: string }[]
  /** Only passed (and rendered) by the edit flow — never on match creation,
   * which always auto-stamps the deck's current version server-side. */
  decklistVersionOptions?: { id: string; version: number }[]
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        <div className="flex flex-col gap-1.5">
          <Label>My deck</Label>
          <Select
            value={draft.personalDeckId}
            onValueChange={(value) => {
              onChange({ ...draft, personalDeckId: value })
            }}
          >
            <SelectTrigger className="w-52">
              <SelectValue placeholder="— select —" />
            </SelectTrigger>
            <SelectContent>
              {personalDeckOptions.map((deck) => (
                <SelectItem key={deck.id} value={deck.id}>
                  {deck.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {decklistVersionOptions && decklistVersionOptions.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <Label>Decklist version</Label>
            <Select
              value={draft.decklistVersionId ?? NO_VERSION_VALUE}
              onValueChange={(value) => {
                onChange({
                  ...draft,
                  decklistVersionId: value === NO_VERSION_VALUE ? null : value,
                })
              }}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_VERSION_VALUE}>— none —</SelectItem>
                {decklistVersionOptions.map((version) => (
                  <SelectItem key={version.id} value={version.id}>
                    v{version.version}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <OpponentDeckField
          value={draft.opponentDeckId}
          onChange={(deckId) => {
            onChange({ ...draft, opponentDeckId: deckId })
          }}
          options={metaDeckOptions}
        />
        <div className="flex flex-col gap-1.5">
          <Label>Play/Draw</Label>
          <Select
            value={draft.onPlay ? 'otp' : 'otd'}
            onValueChange={(value) => {
              onChange({ ...draft, onPlay: value === 'otp' })
            }}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="otp">On the Play</SelectItem>
              <SelectItem value="otd">On the Draw</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <GameResultSelect
          label="Game 1"
          value={draft.game1}
          onChange={(value) => {
            onChange({ ...draft, game1: value })
          }}
        />
        <GameResultSelect
          label="Game 2"
          value={draft.game2}
          onChange={(value) => {
            onChange({ ...draft, game2: value })
          }}
        />
        <GameResultSelect
          label="Game 3"
          value={draft.game3}
          onChange={(value) => {
            onChange({ ...draft, game3: value })
          }}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="opening-hand">Opening hand</Label>
          <Textarea
            id="opening-hand"
            rows={3}
            value={draft.openingHand}
            onChange={(event) => {
              onChange({ ...draft, openingHand: event.target.value })
            }}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="turning-point">Turning point</Label>
          <Textarea
            id="turning-point"
            rows={3}
            value={draft.turningPoint}
            onChange={(event) => {
              onChange({ ...draft, turningPoint: event.target.value })
            }}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="final-turn">Final turn</Label>
          <Textarea
            id="final-turn"
            rows={3}
            value={draft.finalTurn}
            onChange={(event) => {
              onChange({ ...draft, finalTurn: event.target.value })
            }}
          />
        </div>
      </div>
    </div>
  )
}
