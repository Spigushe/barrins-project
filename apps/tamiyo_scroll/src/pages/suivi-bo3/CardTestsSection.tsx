import { type FormEvent, useEffect, useState } from 'react'
import {
  useCardTests,
  useCreateCardTest,
  useDeleteCardTest,
  useUpdateCardTest,
} from '@/hooks/useCardTests'
import { useMetaDecks } from '@/hooks/useMetaDecks'
import { useCurrentUser } from '@/hooks/useAuth'
import { useActiveDeck } from '@/contexts/active-deck-context'
import type { CardTest, CardTestWrite } from '@/schemas/tamiyoScroll'
import { RATING_LABELS, ratingTextClass } from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
const RATINGS = [1, 2, 3, 4, 5]

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

  if (activeDeckId === null) {
    return (
      <Card>
        <CardTitle>Tested cards — individual feedback</CardTitle>
        <CardDescription className="mt-1">
          Select or create a personal deck above to see its test
          feedback.
        </CardDescription>
      </Card>
    )
  }
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
          <div className="flex flex-col gap-1.5">
            <Label>Match-up</Label>
            <Select
              value={newDraft.opponentDeckId}
              onValueChange={(value) => {
                setNewDraft({ ...newDraft, opponentDeckId: value })
              }}
            >
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_MATCHUP}>— none —</SelectItem>
                {deckOptions.map((deck) => (
                  <SelectItem key={deck.id} value={deck.id}>
                    {deck.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
                    <Select
                      value={editDraft.opponentDeckId}
                      onValueChange={(value) => {
                        setEditDraft({ ...editDraft, opponentDeckId: value })
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NO_MATCHUP}>— none —</SelectItem>
                        {deckOptions.map((deck) => (
                          <SelectItem key={deck.id} value={deck.id}>
                            {deck.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
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

            const matchupDeck = deckOptions.find(
              (deck) => deck.id === test.opponent_deck_id,
            )
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
