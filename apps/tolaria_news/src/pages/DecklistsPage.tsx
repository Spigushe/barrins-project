import { useState, type KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'
import { useCommanders, useDecks, useStaples } from '@/hooks/useDecks'
import type { DeckListFilters } from '@/api/decks'
import { Card, CardTitle } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
import { ColorIdentityPicker } from '@/components/color-identity-picker'
import { TournamentSizeFilter } from '@/components/tournament-size-filter'
import { StaplesSection } from '@/components/staples-section'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

const SOURCES = [
  { value: '', label: 'All sources' },
  { value: 'mtgo', label: 'MTGO' },
  { value: 'mtgtop8', label: 'MTGTop8' },
] as const

const inputClass =
  'h-9 rounded-(--radius-input) border border-border bg-input px-2 text-sm text-foreground'

const DEFAULT_FILTERS: DeckListFilters = {}

export function DecklistsPage() {
  const [filters, setFilters] = useState<DeckListFilters>(DEFAULT_FILTERS)
  const [playerInput, setPlayerInput] = useState('')
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const [cursorHistory, setCursorHistory] = useState<(string | undefined)[]>([])

  const { data, isLoading, isError, error } = useDecks(filters, cursor)
  const { data: commanders, isLoading: commandersLoading } = useCommanders()
  const staples = useStaples(
    filters.dateFrom,
    filters.dateTo,
    filters.commander,
    filters.commander !== undefined,
  )

  const isAtDefaultFilters = Object.keys(filters).length === 0 && playerInput === ''

  function updateFilters(next: DeckListFilters) {
    setFilters(next)
    setCursor(undefined)
    setCursorHistory([])
  }

  function resetFilters() {
    updateFilters(DEFAULT_FILTERS)
    setPlayerInput('')
  }

  function commitPlayerFilter() {
    updateFilters({ ...filters, player: playerInput.trim() || undefined })
  }

  function handlePlayerKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') commitPlayerFilter()
  }

  function toggleColor(color: string) {
    const current = filters.colors ?? []
    const next = current.includes(color)
      ? current.filter((c) => c !== color)
      : [...current, color]
    updateFilters({ ...filters, colors: next.length > 0 ? next : undefined })
  }

  function toggleSize(bucket: string) {
    const current = filters.sizes ?? []
    const next = current.includes(bucket)
      ? current.filter((b) => b !== bucket)
      : [...current, bucket]
    updateFilters({ ...filters, sizes: next.length > 0 ? next : undefined })
  }

  function goNext() {
    const nextCursor = data?.page?.next_cursor
    if (!nextCursor) return
    setCursorHistory((history) => [...history, cursor])
    setCursor(nextCursor)
  }

  function goPrevious() {
    setCursorHistory((history) => {
      const next = [...history]
      setCursor(next.pop())
      return next
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-2">
          <Eyebrow>Duel Commander · Decklists</Eyebrow>
          <CardTitle>Every list. Every result.</CardTitle>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={isAtDefaultFilters}
          onClick={resetFilters}
        >
          Reset filters
        </Button>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          Pilot
          <input
            type="text"
            placeholder="Search by pilot name"
            className={inputClass}
            value={playerInput}
            onChange={(e) => setPlayerInput(e.target.value)}
            onBlur={commitPlayerFilter}
            onKeyDown={handlePlayerKeyDown}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          Source
          <select
            className={inputClass}
            value={filters.source ?? ''}
            onChange={(e) => {
              const value = e.target.value
              updateFilters({
                ...filters,
                source: value === '' ? undefined : (value as DeckListFilters['source']),
              })
            }}
          >
            {SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          Commander
          <select
            className={inputClass}
            value={filters.commander ?? ''}
            disabled={commandersLoading}
            onChange={(e) => {
              const value = e.target.value
              updateFilters({ ...filters, commander: value === '' ? undefined : value })
            }}
          >
            <option value="">{commandersLoading ? 'Loading…' : 'All commanders'}</option>
            {commanders?.data.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          From
          <input
            type="date"
            className={inputClass}
            value={filters.dateFrom ?? ''}
            onChange={(e) =>
              updateFilters({ ...filters, dateFrom: e.target.value || undefined })
            }
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          To
          <input
            type="date"
            className={inputClass}
            value={filters.dateTo ?? ''}
            onChange={(e) =>
              updateFilters({ ...filters, dateTo: e.target.value || undefined })
            }
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          Color identity
          <ColorIdentityPicker selected={filters.colors ?? []} onToggle={toggleColor} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          Tournament size
          <TournamentSizeFilter selected={filters.sizes ?? []} onToggle={toggleSize} />
        </label>
      </div>

      {filters.commander !== undefined && (
        <div className="flex flex-col gap-2">
          <CardTitle className="text-base">Staples for {filters.commander}</CardTitle>
          <StaplesSection
            data={staples.data?.data}
            isLoading={staples.isLoading}
            isError={staples.isError}
          />
        </div>
      )}

      {isLoading && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <Card className="border-destructive/40 text-destructive">
          Failed to load decklists{error instanceof Error ? `: ${error.message}` : '.'}
        </Card>
      )}

      {data && (
        <>
          <Card className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Pilot</TableHead>
                  <TableHead>Tournament</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Result</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.data.map((deck) => (
                  <TableRow key={deck.id}>
                    <TableCell>{deck.date}</TableCell>
                    <TableCell>
                      <Link
                        to={`/decks/${deck.id}`}
                        className="font-semibold text-foreground hover:text-accent"
                      >
                        {deck.player}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Link
                        to={`/tournaments/${deck.tournament_id}`}
                        className="text-muted-foreground hover:text-accent"
                      >
                        {deck.tournament_name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="accent">{deck.tournament_source}</Badge>
                    </TableCell>
                    <TableCell>{deck.result ?? '—'}</TableCell>
                  </TableRow>
                ))}
                {data.data.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      No decklists match these filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={cursorHistory.length === 0}
              onClick={goPrevious}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!data.page?.next_cursor}
              onClick={goNext}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
