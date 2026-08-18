import { type FormEvent, useEffect, useState } from 'react'
import {
  useCardTests,
  useCreateCardTest,
  useDeleteCardTest,
  useUpdateCardTest,
} from '@/hooks/useCardTests'
import { resolveMetaDeckOption, useMetaDecks } from '@/hooks/useMetaDecks'
import { useCurrentUser } from '@/hooks/useAuth'
import { useActiveDeck } from '@/contexts/active-deck-context'
import type { CardTest, CardTestWrite, MetaDeck } from '@/schemas/tamiyoScroll'
import { RATING_LABELS, ratingTextClass } from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const NO_MATCHUP = '__none__'
const NO_MATCHUP_LABEL = '— none —'
const RATINGS = [1, 2, 3, 4, 5]

/**
 * Match-up deck field: search existing meta decks, same
 * `Popover`+`Command` combobox shape as `OpponentDeckField`
 * (`MatchForm.tsx`), including the "shared — tap to add to your roster"
 * sub-label for `is_readonly` decks (S12 item 2).
 *
 * Deliberately no inline "Create "…"" affordance — per S12's open
 * question 3, this select is about search/selection parity with the BO3
 * opponent field, not adding a new deck-creation path; selecting any
 * option (including a shared one) directly sets the matchup, same as
 * this select's previous plain-`<Select>` behavior.
 */
function MatchupDeckField({
  value,
  onChange,
  options,
  idPrefix,
  visibleLabel,
  triggerClassName,
}: {
  value: string
  onChange: (deckId: string) => void
  options: MetaDeck[]
  idPrefix: string
  /** Create form shows a standalone `<Label>`; the edit row (inside a
   * table cell) only needs an accessible name via `aria-label`. */
  visibleLabel: boolean
  triggerClassName?: string
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  const selected = resolveMetaDeckOption(options, value)
  const selectedLabel =
    value === NO_MATCHUP ? NO_MATCHUP_LABEL : (selected?.name ?? NO_MATCHUP_LABEL)
  const trimmedSearch = search.trim()
  const filtered = options.filter((deck) =>
    deck.name.toLowerCase().includes(trimmedSearch.toLowerCase()),
  )

  function selectDeck(deckId: string) {
    onChange(deckId)
    setOpen(false)
    setSearch('')
  }

  const labelId = `${idPrefix}-label`

  return (
    <div className="flex flex-col gap-1.5">
      {visibleLabel && <Label id={labelId}>Match-up</Label>}
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (!next) setSearch('')
        }}
      >
        <PopoverTrigger
          aria-labelledby={visibleLabel ? labelId : undefined}
          aria-label={visibleLabel ? undefined : 'Match-up'}
          className={cn(
            'flex h-9 items-center justify-between gap-2 rounded-(--radius-input) border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors',
            'focus-visible:border-accent',
            triggerClassName ?? 'w-44',
          )}
        >
          <span className="min-w-0 flex-1 truncate text-left">{selectedLabel}</span>
        </PopoverTrigger>
        <PopoverContent className="p-0">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search…"
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              <CommandGroup>
                <CommandItem
                  value={NO_MATCHUP}
                  onSelect={() => {
                    selectDeck(NO_MATCHUP)
                  }}
                >
                  {value === NO_MATCHUP ? '✓ ' : ''}
                  {NO_MATCHUP_LABEL}
                </CommandItem>
                {filtered.map((deck) => (
                  <CommandItem
                    key={deck.id}
                    value={deck.id}
                    onSelect={() => {
                      selectDeck(deck.id)
                    }}
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span>
                        {deck.id === value || deck.merged_ids?.includes(value)
                          ? '✓ '
                          : ''}
                        {deck.name}
                      </span>
                      {deck.is_readonly && (
                        <span className="text-[11px] text-muted-foreground">
                          shared — tap to add to your roster
                        </span>
                      )}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
              {filtered.length === 0 && trimmedSearch && (
                <CommandEmpty>No match found.</CommandEmpty>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  )
}

interface Draft {
  tester: string
  cardName: string
  opponentDeckId: string
  rating: number
  notes: string
}

function emptyDraft(tester = ''): Draft {
  return { tester, cardName: '', opponentDeckId: NO_MATCHUP, rating: 3, notes: '' }
}

function draftFromTest(test: CardTest): Draft {
  return {
    tester: test.tester,
    cardName: test.card_name,
    opponentDeckId: test.opponent_deck_id ?? NO_MATCHUP,
    rating: test.rating,
    notes: test.notes ?? '',
  }
}

function toWrite(deckId: string, draft: Draft): CardTestWrite {
  return {
    personal_deck_id: deckId,
    tester: draft.tester.trim(),
    card_name: draft.cardName.trim(),
    opponent_deck_id: draft.opponentDeckId === NO_MATCHUP ? null : draft.opponentDeckId,
    rating: draft.rating,
    notes: draft.notes.trim() || null,
  }
}

export function CardTestsSection() {
  const { canEdit, activeDeckId } = useActiveDeck()
  const { data: cardTests } = useCardTests(activeDeckId)
  const { data: metaDecks } = useMetaDecks()
  const { data: currentUser } = useCurrentUser()
  const createTest = useCreateCardTest()
  const updateTest = useUpdateCardTest()
  const deleteTest = useDeleteCardTest()

  const defaultTester = currentUser?.display_name?.trim() || ''

  const [newDraft, setNewDraft] = useState<Draft>(emptyDraft(defaultTester))
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<Draft>(emptyDraft())

  useEffect(() => {
    setNewDraft((draft) => {
      if (draft.tester || !defaultTester) {
        return draft
      }
      return { ...draft, tester: defaultTester }
    })
  }, [defaultTester])

  const deckOptions = metaDecks ?? []

  if (activeDeckId === null) return null
  const deckId = activeDeckId

  async function handleAdd(event: FormEvent) {
    event.preventDefault()
    if (!newDraft.tester.trim() || !newDraft.cardName.trim()) return
    await createTest.mutateAsync(toWrite(deckId, newDraft))
    setNewDraft(emptyDraft(defaultTester))
  }

  function startEdit(test: CardTest) {
    setEditingId(test.id)
    setEditDraft(draftFromTest(test))
  }

  async function handleSaveEdit(testId: string) {
    await updateTest.mutateAsync({ testId, payload: toWrite(deckId, editDraft) })
    setEditingId(null)
  }

  return (
    <Card>
      <CardTitle>Tested cards — individual feedback</CardTitle>

      {canEdit && (
        <form
          className="mt-3 flex flex-wrap items-end gap-2 rounded-(--radius-input) border border-border-dashed p-3"
          onSubmit={(event) => {
            void handleAdd(event)
          }}
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="test-tester">Nickname</Label>
            <Input
              id="test-tester"
              value={newDraft.tester}
              onChange={(event) => {
                setNewDraft({ ...newDraft, tester: event.target.value })
              }}
              className="w-32"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="test-card">Card name</Label>
            <Input
              id="test-card"
              value={newDraft.cardName}
              onChange={(event) => {
                setNewDraft({ ...newDraft, cardName: event.target.value })
              }}
              className="w-48"
            />
          </div>
          <MatchupDeckField
            value={newDraft.opponentDeckId}
            onChange={(value) => {
              setNewDraft({ ...newDraft, opponentDeckId: value })
            }}
            options={deckOptions}
            idPrefix="new-test-matchup"
            visibleLabel
          />
          <div className="flex flex-col gap-1.5">
            <Label>Effectiveness</Label>
            <Select
              value={String(newDraft.rating)}
              onValueChange={(value) => {
                setNewDraft({ ...newDraft, rating: Number(value) })
              }}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RATINGS.map((rating) => (
                  <SelectItem key={rating} value={String(rating)}>
                    {RATING_LABELS[rating]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-1 flex-col gap-1.5">
            <Label htmlFor="test-notes">Notes</Label>
            <Input
              id="test-notes"
              value={newDraft.notes}
              onChange={(event) => {
                setNewDraft({ ...newDraft, notes: event.target.value })
              }}
            />
          </div>
          <Button type="submit" disabled={createTest.isPending}>
            Add
          </Button>
        </form>
      )}

      <Table className="mt-3">
        <TableHeader>
          <TableRow>
            <TableHead>Nickname</TableHead>
            <TableHead>Card</TableHead>
            <TableHead>Match-up</TableHead>
            <TableHead className="w-32">Effectiveness</TableHead>
            <TableHead>Notes</TableHead>
            {canEdit && <TableHead className="w-36" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {cardTests?.map((test) => {
            const isEditing = editingId === test.id
            if (isEditing) {
              return (
                <TableRow key={test.id}>
                  <TableCell>
                    <Input
                      value={editDraft.tester}
                      onChange={(event) => {
                        setEditDraft({ ...editDraft, tester: event.target.value })
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      value={editDraft.cardName}
                      onChange={(event) => {
                        setEditDraft({ ...editDraft, cardName: event.target.value })
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <MatchupDeckField
                      value={editDraft.opponentDeckId}
                      onChange={(value) => {
                        setEditDraft({ ...editDraft, opponentDeckId: value })
                      }}
                      options={deckOptions}
                      idPrefix={`edit-test-matchup-${test.id}`}
                      visibleLabel={false}
                      triggerClassName="w-full"
                    />
                  </TableCell>
                  <TableCell>
                    <Select
                      value={String(editDraft.rating)}
                      onValueChange={(value) => {
                        setEditDraft({ ...editDraft, rating: Number(value) })
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RATINGS.map((rating) => (
                          <SelectItem key={rating} value={String(rating)}>
                            {RATING_LABELS[rating]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Input
                      value={editDraft.notes}
                      onChange={(event) => {
                        setEditDraft({ ...editDraft, notes: event.target.value })
                      }}
                    />
                  </TableCell>
                  <TableCell className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      disabled={updateTest.isPending}
                      onClick={() => {
                        void handleSaveEdit(test.id)
                      }}
                    >
                      Save
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setEditingId(null)
                      }}
                    >
                      Cancel
                    </Button>
                  </TableCell>
                </TableRow>
              )
            }

            const matchupDeck = resolveMetaDeckOption(deckOptions, test.opponent_deck_id)
            return (
              <TableRow key={test.id}>
                <TableCell>{test.tester}</TableCell>
                <TableCell className="font-mono">{test.card_name}</TableCell>
                <TableCell>{matchupDeck?.name ?? '—'}</TableCell>
                <TableCell className={cn('font-semibold', ratingTextClass(test.rating))}>
                  {RATING_LABELS[test.rating]}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {test.notes ?? '—'}
                </TableCell>
                {canEdit && (
                  <TableCell className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        startEdit(test)
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        void deleteTest.mutateAsync(test.id)
                      }}
                    >
                      ✕
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            )
          })}
          {(cardTests?.length ?? 0) === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground">
                No test feedback.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Card>
  )
}
