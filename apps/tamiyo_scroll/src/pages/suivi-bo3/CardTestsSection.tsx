import { Fragment, type FormEvent, useState } from 'react'
import {
  useCardTests,
  useCreateCardTest,
  useCreateCardTestEvaluation,
  useDeleteCardTest,
  useDeleteCardTestEvaluation,
  useUpdateCardTest,
  useUpdateCardTestEvaluation,
} from '@/hooks/useCardTests'
import { CARD_NAME_SEARCH_MIN_LENGTH, useCardNameSearch } from '@/hooks/useCards'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { useDecklistView } from '@/hooks/useDecklistVersions'
import { resolveMetaDeckOption, useMetaDecks } from '@/hooks/useMetaDecks'
import { useActiveDeck } from '@/contexts/active-deck-context'
import { ApiError } from '@/api/client'
import type {
  CardTest,
  CardTestEvaluation,
  CardTestEvaluationWrite,
  CardTestWrite,
  DecklistView,
  MetaDeck,
} from '@/schemas/tamiyoScroll'
import { RATING_LABELS, ratingTextClass } from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { CardNameHover } from '@/components/card-name-hover'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
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
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
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
 *
 * Reused for evaluations (S17): an evaluation's `opponent_deck_id` is
 * required, so `NO_MATCHUP` there means "not yet chosen" rather than a
 * valid "no matchup" value — callers gate submission on it themselves.
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

/** Every distinct card name currently on the deck's latest decklist —
 * source for the Removed-Card dropdown (S17 item 2), client-side over
 * data the tab already fetches, no extra request. */
function decklistCardNames(view: DecklistView | undefined): string[] {
  if (!view) return []
  const names = new Set<string>()
  for (const card of view.commander_cards) names.add(card.name)
  for (const group of view.library_cards) {
    for (const card of group.cards) names.add(card.name)
  }
  return [...names]
}

const CARD_NAME_SUGGESTION_LIMIT = 20

function filterCardNames(names: string[], query: string): string[] {
  const trimmed = query.trim().toLowerCase()
  if (!trimmed) return []
  return names
    .filter((name) => name.toLowerCase().includes(trimmed))
    .slice(0, CARD_NAME_SUGGESTION_LIMIT)
}

/** S17 item 2: "not found" warning for the Added-Card dropdown once its
 * live search has actually run and come back empty — never shown while
 * still below the minimum length or mid-fetch, so it can't flash on
 * every keystroke. */
function addedCardNotFoundHint(
  debouncedQuery: string,
  search: { data?: string[]; isFetching: boolean },
): string | null {
  if (debouncedQuery.trim().length < CARD_NAME_SEARCH_MIN_LENGTH) return null
  if (search.isFetching) return null
  if (search.data && search.data.length === 0) {
    return 'No matching card found — you can still save this name.'
  }
  return null
}

/**
 * Free-text card-name input with a suggestion dropdown (S17 item 2) —
 * unlike `MatchupDeckField`'s select-only combobox, the input itself
 * *is* the value (typing freely stays valid; S16's opt-in validations
 * are the real enforcement), suggestions are just a shortcut onto it.
 * `PopoverAnchor` wraps the real `Input` so the dropdown positions off
 * it without stealing its focus or replacing it with a separate search
 * box.
 */
function CardNameField({
  id,
  label,
  value,
  onChange,
  suggestions,
  notFoundHint = null,
  showLabel = true,
  className,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  suggestions: string[]
  notFoundHint?: string | null
  showLabel?: boolean
  className?: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex flex-col gap-1.5">
      {showLabel && <Label htmlFor={id}>{label}</Label>}
      <Popover open={open && suggestions.length > 0}>
        <PopoverAnchor asChild>
          <Input
            id={id}
            aria-label={showLabel ? undefined : label}
            value={value}
            autoComplete="off"
            className={className}
            onChange={(event) => {
              onChange(event.target.value)
              setOpen(true)
            }}
            onFocus={() => {
              setOpen(true)
            }}
            onBlur={() => {
              setOpen(false)
            }}
          />
        </PopoverAnchor>
        <PopoverContent
          className="max-h-64 overflow-y-auto p-1"
          onOpenAutoFocus={(event) => {
            event.preventDefault()
          }}
        >
          {suggestions.map((name) => (
            <button
              key={name}
              type="button"
              className="block w-full truncate rounded-sm px-2 py-1.5 text-left text-sm hover:bg-input"
              // Prevents the input from blurring (and the popover closing)
              // before the click's onChange-equivalent below can fire.
              onMouseDown={(event) => {
                event.preventDefault()
              }}
              onClick={() => {
                onChange(name)
                setOpen(false)
              }}
            >
              {name}
            </button>
          ))}
        </PopoverContent>
      </Popover>
      {notFoundHint && (
        <p className="text-[11px] text-muted-foreground">{notFoundHint}</p>
      )}
    </div>
  )
}

interface Draft {
  removedCardName: string
  addedCardName: string
  notes: string
}

function emptyDraft(): Draft {
  return { removedCardName: '', addedCardName: '', notes: '' }
}

function draftFromTest(test: CardTest): Draft {
  return {
    removedCardName: test.removed_card_name,
    addedCardName: test.added_card_name,
    notes: test.notes ?? '',
  }
}

function toWrite(deckId: string, draft: Draft): CardTestWrite {
  return {
    personal_deck_id: deckId,
    removed_card_name: draft.removedCardName.trim(),
    added_card_name: draft.addedCardName.trim(),
    notes: draft.notes.trim() || null,
  }
}

interface EvalDraft {
  opponentDeckId: string
  rating: number
  notes: string
}

function emptyEvalDraft(): EvalDraft {
  return { opponentDeckId: NO_MATCHUP, rating: 3, notes: '' }
}

function evalDraftFromEvaluation(evaluation: CardTestEvaluation): EvalDraft {
  return {
    opponentDeckId: evaluation.opponent_deck_id,
    rating: evaluation.rating,
    notes: evaluation.notes ?? '',
  }
}

/** `null` while `opponentDeckId` is still the unselected sentinel — an
 * evaluation's matchup is required, unlike the pre-S17 flat field. */
function toEvalWrite(draft: EvalDraft): CardTestEvaluationWrite | null {
  if (draft.opponentDeckId === NO_MATCHUP) return null
  return {
    opponent_deck_id: draft.opponentDeckId,
    rating: draft.rating,
    notes: draft.notes.trim() || null,
  }
}

function errorMessage(error: unknown): string | null {
  if (error instanceof ApiError) return error.message
  return null
}

export function CardTestsSection() {
  const { canEdit, activeDeckId } = useActiveDeck()
  const { data: cardTests } = useCardTests(activeDeckId)
  const { data: metaDecks } = useMetaDecks()
  const { data: decklistView } = useDecklistView(activeDeckId)
  const createTest = useCreateCardTest()
  const updateTest = useUpdateCardTest()
  const deleteTest = useDeleteCardTest()
  const createEvaluation = useCreateCardTestEvaluation()
  const updateEvaluation = useUpdateCardTestEvaluation()
  const deleteEvaluation = useDeleteCardTestEvaluation()

  const [newDraft, setNewDraft] = useState<Draft>(emptyDraft())
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<Draft>(emptyDraft())
  const [pendingDelete, setPendingDelete] = useState<CardTest | null>(null)

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [newEvalDraft, setNewEvalDraft] = useState<EvalDraft>(emptyEvalDraft())
  const [editingEvalId, setEditingEvalId] = useState<string | null>(null)
  const [editEvalDraft, setEditEvalDraft] = useState<EvalDraft>(emptyEvalDraft())
  const [pendingDeleteEval, setPendingDeleteEval] = useState<{
    testId: string
    evaluation: CardTestEvaluation
  } | null>(null)

  const deckOptions = metaDecks ?? []
  const decklistNames = decklistCardNames(decklistView)

  const debouncedNewAddedCard = useDebouncedValue(newDraft.addedCardName, 250)
  const newAddedCardSearch = useCardNameSearch(debouncedNewAddedCard)
  const debouncedEditAddedCard = useDebouncedValue(editDraft.addedCardName, 250)
  const editAddedCardSearch = useCardNameSearch(debouncedEditAddedCard)

  if (activeDeckId === null) return null
  const deckId = activeDeckId

  async function handleAdd(event: FormEvent) {
    event.preventDefault()
    if (!newDraft.removedCardName.trim() || !newDraft.addedCardName.trim()) return
    await createTest.mutateAsync(toWrite(deckId, newDraft))
    setNewDraft(emptyDraft())
  }

  function startEdit(test: CardTest) {
    setEditingId(test.id)
    setEditDraft(draftFromTest(test))
  }

  async function handleSaveEdit(testId: string) {
    await updateTest.mutateAsync({ testId, payload: toWrite(deckId, editDraft) })
    setEditingId(null)
  }

  function toggleExpand(testId: string) {
    setExpandedId((current) => (current === testId ? null : testId))
    setNewEvalDraft(emptyEvalDraft())
    setEditingEvalId(null)
  }

  async function handleAddEvaluation(testId: string) {
    const payload = toEvalWrite(newEvalDraft)
    if (!payload) return
    await createEvaluation.mutateAsync({ testId, payload })
    setNewEvalDraft(emptyEvalDraft())
  }

  function startEditEval(evaluation: CardTestEvaluation) {
    setEditingEvalId(evaluation.id)
    setEditEvalDraft(evalDraftFromEvaluation(evaluation))
  }

  async function handleSaveEditEval(testId: string, evaluationId: string) {
    const payload = toEvalWrite(editEvalDraft)
    if (!payload) return
    await updateEvaluation.mutateAsync({ testId, evaluationId, payload })
    setEditingEvalId(null)
  }

  return (
    <Card>
      <CardTitle>Tested cards — card log</CardTitle>

      {canEdit && (
        <form
          className="mt-3 flex flex-wrap items-end gap-2 rounded-(--radius-input) border border-border-dashed p-3"
          onSubmit={(event) => {
            void handleAdd(event)
          }}
        >
          <CardNameField
            id="test-removed-card"
            label="Removed Card"
            value={newDraft.removedCardName}
            onChange={(value) => {
              setNewDraft({ ...newDraft, removedCardName: value })
            }}
            suggestions={filterCardNames(decklistNames, newDraft.removedCardName)}
            className="w-32"
          />
          <CardNameField
            id="test-added-card"
            label="Added Card"
            value={newDraft.addedCardName}
            onChange={(value) => {
              setNewDraft({ ...newDraft, addedCardName: value })
            }}
            suggestions={newAddedCardSearch.data ?? []}
            notFoundHint={addedCardNotFoundHint(
              debouncedNewAddedCard,
              newAddedCardSearch,
            )}
            className="w-48"
          />
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
          {errorMessage(createTest.error) && (
            <p className="w-full text-[12.5px] text-destructive">
              {errorMessage(createTest.error)}
            </p>
          )}
        </form>
      )}

      <Table className="mt-3">
        <TableHeader>
          <TableRow>
            <TableHead>Removed Card</TableHead>
            <TableHead>Added Card</TableHead>
            <TableHead>Notes</TableHead>
            <TableHead className="w-40">Evaluations</TableHead>
            {canEdit && <TableHead className="w-36" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {cardTests?.map((test) => {
            const isEditing = editingId === test.id
            const isExpanded = expandedId === test.id

            if (isEditing) {
              return (
                <TableRow key={test.id}>
                  <TableCell>
                    <CardNameField
                      id={`edit-removed-card-${test.id}`}
                      label="Removed Card"
                      showLabel={false}
                      value={editDraft.removedCardName}
                      onChange={(value) => {
                        setEditDraft({ ...editDraft, removedCardName: value })
                      }}
                      suggestions={filterCardNames(
                        decklistNames,
                        editDraft.removedCardName,
                      )}
                    />
                  </TableCell>
                  <TableCell>
                    <CardNameField
                      id={`edit-added-card-${test.id}`}
                      label="Added Card"
                      showLabel={false}
                      value={editDraft.addedCardName}
                      onChange={(value) => {
                        setEditDraft({ ...editDraft, addedCardName: value })
                      }}
                      suggestions={editAddedCardSearch.data ?? []}
                      notFoundHint={addedCardNotFoundHint(
                        debouncedEditAddedCard,
                        editAddedCardSearch,
                      )}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      value={editDraft.notes}
                      onChange={(event) => {
                        setEditDraft({ ...editDraft, notes: event.target.value })
                      }}
                    />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {test.evaluations.length}
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
                    {errorMessage(updateTest.error) && (
                      <p className="w-full text-[12.5px] text-destructive">
                        {errorMessage(updateTest.error)}
                      </p>
                    )}
                  </TableCell>
                </TableRow>
              )
            }

            return (
              <Fragment key={test.id}>
                <TableRow>
                  <TableCell>
                    <CardNameHover
                      name={test.removed_card_name}
                      scryfallId={test.removed_card_scryfall_id}
                    />
                  </TableCell>
                  <TableCell className="font-mono">
                    <CardNameHover
                      name={test.added_card_name}
                      scryfallId={test.added_card_scryfall_id}
                    />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {test.notes ?? '—'}
                  </TableCell>
                  <TableCell>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        toggleExpand(test.id)
                      }}
                    >
                      {test.evaluations.length} {isExpanded ? '▾' : '▸'}
                    </Button>
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
                          setPendingDelete(test)
                        }}
                      >
                        ✕
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
                {isExpanded && (
                  <TableRow>
                    <TableCell colSpan={canEdit ? 5 : 4} className="bg-input-inline">
                      <div className="flex flex-col gap-2 py-1">
                        {test.evaluations.map((evaluation) => {
                          const isEditingEval = editingEvalId === evaluation.id
                          const matchupDeck = resolveMetaDeckOption(
                            deckOptions,
                            evaluation.opponent_deck_id,
                          )
                          if (isEditingEval) {
                            return (
                              <div
                                key={evaluation.id}
                                className="flex flex-wrap items-end gap-2"
                              >
                                <MatchupDeckField
                                  value={editEvalDraft.opponentDeckId}
                                  onChange={(value) => {
                                    setEditEvalDraft({
                                      ...editEvalDraft,
                                      opponentDeckId: value,
                                    })
                                  }}
                                  options={deckOptions}
                                  idPrefix={`edit-eval-matchup-${evaluation.id}`}
                                  visibleLabel={false}
                                />
                                <Select
                                  value={String(editEvalDraft.rating)}
                                  onValueChange={(value) => {
                                    setEditEvalDraft({
                                      ...editEvalDraft,
                                      rating: Number(value),
                                    })
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
                                <Input
                                  className="flex-1"
                                  value={editEvalDraft.notes}
                                  onChange={(event) => {
                                    setEditEvalDraft({
                                      ...editEvalDraft,
                                      notes: event.target.value,
                                    })
                                  }}
                                />
                                <Button
                                  type="button"
                                  size="sm"
                                  disabled={
                                    updateEvaluation.isPending ||
                                    editEvalDraft.opponentDeckId === NO_MATCHUP
                                  }
                                  onClick={() => {
                                    void handleSaveEditEval(test.id, evaluation.id)
                                  }}
                                >
                                  Save
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    setEditingEvalId(null)
                                  }}
                                >
                                  Cancel
                                </Button>
                                {errorMessage(updateEvaluation.error) && (
                                  <p className="w-full text-[12.5px] text-destructive">
                                    {errorMessage(updateEvaluation.error)}
                                  </p>
                                )}
                              </div>
                            )
                          }
                          return (
                            <div
                              key={evaluation.id}
                              className="flex flex-wrap items-center gap-3"
                            >
                              <span className="w-44 truncate">
                                {matchupDeck?.name ?? '—'}
                              </span>
                              <span
                                className={cn(
                                  'w-32 font-semibold',
                                  ratingTextClass(evaluation.rating),
                                )}
                              >
                                {RATING_LABELS[evaluation.rating]}
                              </span>
                              <span className="flex-1 text-muted-foreground">
                                {evaluation.notes ?? '—'}
                              </span>
                              {canEdit && (
                                <div className="flex gap-2">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                      startEditEval(evaluation)
                                    }}
                                  >
                                    Edit
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => {
                                      setPendingDeleteEval({
                                        testId: test.id,
                                        evaluation,
                                      })
                                    }}
                                  >
                                    ✕
                                  </Button>
                                </div>
                              )}
                            </div>
                          )
                        })}
                        {test.evaluations.length === 0 && (
                          <p className="text-[12.5px] text-muted-foreground">
                            No evaluations yet.
                          </p>
                        )}

                        {canEdit && (
                          <div className="mt-1 flex flex-wrap items-end gap-2 border-t border-border-dashed pt-2">
                            <MatchupDeckField
                              value={newEvalDraft.opponentDeckId}
                              onChange={(value) => {
                                setNewEvalDraft({
                                  ...newEvalDraft,
                                  opponentDeckId: value,
                                })
                              }}
                              options={deckOptions}
                              idPrefix={`new-eval-matchup-${test.id}`}
                              visibleLabel
                            />
                            <div className="flex flex-col gap-1.5">
                              <Label>Effectiveness</Label>
                              <Select
                                value={String(newEvalDraft.rating)}
                                onValueChange={(value) => {
                                  setNewEvalDraft({
                                    ...newEvalDraft,
                                    rating: Number(value),
                                  })
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
                              <Label htmlFor={`new-eval-notes-${test.id}`}>Notes</Label>
                              <Input
                                id={`new-eval-notes-${test.id}`}
                                value={newEvalDraft.notes}
                                onChange={(event) => {
                                  setNewEvalDraft({
                                    ...newEvalDraft,
                                    notes: event.target.value,
                                  })
                                }}
                              />
                            </div>
                            <Button
                              type="button"
                              size="sm"
                              disabled={
                                createEvaluation.isPending ||
                                newEvalDraft.opponentDeckId === NO_MATCHUP
                              }
                              onClick={() => {
                                void handleAddEvaluation(test.id)
                              }}
                            >
                              Add evaluation
                            </Button>
                            {errorMessage(createEvaluation.error) && (
                              <p className="w-full text-[12.5px] text-destructive">
                                {errorMessage(createEvaluation.error)}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            )
          })}
          {(cardTests?.length ?? 0) === 0 && (
            <TableRow>
              <TableCell
                colSpan={canEdit ? 5 : 4}
                className="text-center text-muted-foreground"
              >
                No test feedback.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(next) => {
          if (!next) setPendingDelete(null)
        }}
        title={pendingDelete ? `Delete "${pendingDelete.added_card_name}"?` : ''}
        description="It will disappear from this deck's test feedback, along with any evaluations logged against it."
        confirmDisabled={deleteTest.isPending}
        onConfirm={() => {
          if (!pendingDelete) return
          void deleteTest.mutateAsync(pendingDelete.id)
          setPendingDelete(null)
        }}
      />

      <ConfirmDialog
        open={pendingDeleteEval !== null}
        onOpenChange={(next) => {
          if (!next) setPendingDeleteEval(null)
        }}
        title="Delete this evaluation?"
        description="It will disappear from this card log's evaluations."
        confirmDisabled={deleteEvaluation.isPending}
        onConfirm={() => {
          if (!pendingDeleteEval) return
          void deleteEvaluation.mutateAsync({
            testId: pendingDeleteEval.testId,
            evaluationId: pendingDeleteEval.evaluation.id,
          })
          setPendingDeleteEval(null)
        }}
      />
    </Card>
  )
}
