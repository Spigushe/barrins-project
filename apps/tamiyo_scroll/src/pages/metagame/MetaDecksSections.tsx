import { type FormEvent, useState } from 'react'
import {
  useArchiveMetaDeck,
  useCreateMetaDeck,
  useMetaDecks,
  useUpdateMetaDeck,
} from '@/hooks/useMetaDecks'
import { useActiveDeck } from '@/contexts/active-deck-context'
import type {
  ArchetypeCategory,
  ExpectedLevel,
  MetaDeck,
  MetaDeckWrite,
} from '@/schemas/tamiyoScroll'
import { ARCHETYPE_LABELS, EXPECTED_LABELS, formatPercent } from '@/lib/mtg-format'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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

const TIERS = [0, 0.5, 1, 1.5, 2, 2.5, 3]

const ARCHETYPE_OPTIONS = Object.keys(ARCHETYPE_LABELS) as ArchetypeCategory[]
const EXPECTED_OPTIONS = Object.keys(EXPECTED_LABELS) as ExpectedLevel[]

function toWrite(deck: MetaDeck, overrides: Partial<MetaDeckWrite> = {}): MetaDeckWrite {
  return {
    name: deck.name,
    tier: deck.tier,
    category: deck.category,
    decklist_notes: deck.decklist_notes,
    top8: deck.top8,
    presence: deck.presence,
    expected: deck.expected,
    tests_status: deck.tests_status,
    ...overrides,
  }
}

export function MetaDecksRosterSection() {
  const { canEdit } = useActiveDeck()
  const { data: metaDecks } = useMetaDecks()
  const createDeck = useCreateMetaDeck()
  const updateDeck = useUpdateMetaDeck()
  const archiveDeck = useArchiveMetaDeck()

  const [newName, setNewName] = useState('')
  const [newTier, setNewTier] = useState(1)
  const [newCategory, setNewCategory] = useState<ArchetypeCategory>('midrange')

  async function handleAdd(event: FormEvent) {
    event.preventDefault()
    if (!newName.trim()) return
    await createDeck.mutateAsync({
      name: newName.trim(),
      tier: newTier,
      category: newCategory,
      decklist_notes: null,
      top8: 0,
      presence: 0,
      expected: 'as_expected',
      tests_status: null,
    })
    setNewName('')
    setNewTier(1)
    setNewCategory('midrange')
  }

  return (
    <Card>
      <CardTitle>Deck roster (MUR)</CardTitle>
      <Table className="mt-3">
        <TableHeader>
          <TableRow>
            <TableHead className="w-20">Tier</TableHead>
            <TableHead>Deck</TableHead>
            <TableHead className="w-44">Archetype</TableHead>
            <TableHead>Decklist / notes</TableHead>
            {canEdit && <TableHead className="w-10" />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {metaDecks?.map((deck) => (
            <RosterRow
              key={deck.id}
              deck={deck}
              canEdit={canEdit}
              onSave={(payload) => {
                void updateDeck.mutateAsync({ deckId: deck.id, payload })
              }}
              onDelete={() => {
                void archiveDeck.mutateAsync(deck.id)
              }}
            />
          ))}
        </TableBody>
      </Table>

      {canEdit && (
        <form
          className="mt-3 flex flex-wrap items-end gap-2 border-t border-border-dashed pt-3"
          onSubmit={(event) => {
            void handleAdd(event)
          }}
        >
          <Select
            value={String(newTier)}
            onValueChange={(value) => {
              setNewTier(Number(value))
            }}
          >
            <SelectTrigger className="w-20">
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
          <Input
            placeholder="Opponent deck name"
            value={newName}
            onChange={(event) => {
              setNewName(event.target.value)
            }}
            className="max-w-64"
          />
          <Select
            value={newCategory}
            onValueChange={(value) => {
              setNewCategory(value as ArchetypeCategory)
            }}
          >
            <SelectTrigger className="w-44">
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
          <Button type="submit" disabled={createDeck.isPending}>
            +
          </Button>
        </form>
      )}
    </Card>
  )
}

function RosterRow({
  deck,
  canEdit,
  onSave,
  onDelete,
}: {
  deck: MetaDeck
  canEdit: boolean
  onSave: (payload: MetaDeckWrite) => void
  onDelete: () => void
}) {
  const [name, setName] = useState(deck.name)
  const [notes, setNotes] = useState(deck.decklist_notes ?? '')

  return (
    <TableRow>
      <TableCell>
        <Select
          value={String(deck.tier)}
          onValueChange={(value) => {
            onSave(toWrite(deck, { tier: Number(value) }))
          }}
          disabled={!canEdit}
        >
          <SelectTrigger>
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
      </TableCell>
      <TableCell>
        <Input
          value={name}
          onChange={(event) => {
            setName(event.target.value)
          }}
          onBlur={() => {
            if (name.trim() && name !== deck.name)
              onSave(toWrite(deck, { name: name.trim() }))
          }}
          disabled={!canEdit}
        />
      </TableCell>
      <TableCell>
        <Select
          value={deck.category}
          onValueChange={(value) => {
            onSave(toWrite(deck, { category: value as ArchetypeCategory }))
          }}
          disabled={!canEdit}
        >
          <SelectTrigger>
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
      </TableCell>
      <TableCell>
        <Input
          value={notes}
          onChange={(event) => {
            setNotes(event.target.value)
          }}
          onBlur={() => {
            if (notes !== (deck.decklist_notes ?? '')) {
              onSave(toWrite(deck, { decklist_notes: notes || null }))
            }
          }}
          disabled={!canEdit}
        />
      </TableCell>
      {canEdit && (
        <TableCell>
          <Button type="button" variant="ghost" size="icon" onClick={onDelete}>
            ✕
          </Button>
        </TableCell>
      )}
    </TableRow>
  )
}

export function ExpectedMetagameSection() {
  const { canEdit } = useActiveDeck()
  const { data: metaDecks } = useMetaDecks()
  const updateDeck = useUpdateMetaDeck()

  return (
    <Card>
      <CardTitle>Expected metagame</CardTitle>
      <Table className="mt-3">
        <TableHeader>
          <TableRow>
            <TableHead>Deck</TableHead>
            <TableHead className="w-24">Top 8</TableHead>
            <TableHead className="w-24">Presence</TableHead>
            <TableHead className="w-24">Conversion</TableHead>
            <TableHead className="w-44">Expected</TableHead>
            <TableHead>Tests</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {metaDecks?.map((deck) => (
            <ExpectedRow
              key={deck.id}
              deck={deck}
              canEdit={canEdit}
              onSave={(payload) => {
                void updateDeck.mutateAsync({ deckId: deck.id, payload })
              }}
            />
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

function ExpectedRow({
  deck,
  canEdit,
  onSave,
}: {
  deck: MetaDeck
  canEdit: boolean
  onSave: (payload: MetaDeckWrite) => void
}) {
  const [top8, setTop8] = useState(String(deck.top8))
  const [presence, setPresence] = useState(String(deck.presence))
  const [testsStatus, setTestsStatus] = useState(deck.tests_status ?? '')

  return (
    <TableRow>
      <TableCell>{deck.name}</TableCell>
      <TableCell>
        <Input
          type="number"
          min={0}
          value={top8}
          onChange={(event) => {
            setTop8(event.target.value)
          }}
          onBlur={() => {
            const next = Math.max(0, Number(top8) || 0)
            if (next !== deck.top8) onSave(toWrite(deck, { top8: next }))
          }}
          disabled={!canEdit}
        />
      </TableCell>
      <TableCell>
        <Input
          type="number"
          min={0}
          value={presence}
          onChange={(event) => {
            setPresence(event.target.value)
          }}
          onBlur={() => {
            const next = Math.max(0, Number(presence) || 0)
            if (next !== deck.presence) onSave(toWrite(deck, { presence: next }))
          }}
          disabled={!canEdit}
        />
      </TableCell>
      <TableCell className="font-mono">{formatPercent(deck.conversion)}</TableCell>
      <TableCell>
        <Select
          value={deck.expected}
          onValueChange={(value) => {
            onSave(toWrite(deck, { expected: value as ExpectedLevel }))
          }}
          disabled={!canEdit}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {EXPECTED_OPTIONS.map((level) => (
              <SelectItem key={level} value={level}>
                {EXPECTED_LABELS[level]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </TableCell>
      <TableCell>
        <Input
          value={testsStatus}
          onChange={(event) => {
            setTestsStatus(event.target.value)
          }}
          onBlur={() => {
            if (testsStatus !== (deck.tests_status ?? '')) {
              onSave(toWrite(deck, { tests_status: testsStatus || null }))
            }
          }}
          disabled={!canEdit}
        />
      </TableCell>
    </TableRow>
  )
}
