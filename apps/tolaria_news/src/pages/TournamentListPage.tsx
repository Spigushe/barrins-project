import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTournaments } from '@/hooks/useTournaments'
import type { TournamentListFilters } from '@/api/tournaments'
import { Card, CardTitle } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
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

// Tolaria News only covers Duel Commander (per apps/tolaria_news/README.md) —
// format is fixed, not a user-facing filter.
const DEFAULT_FILTERS: TournamentListFilters = { format: 'Duel Commander' }

export function TournamentListPage() {
  const [filters, setFilters] = useState<TournamentListFilters>(DEFAULT_FILTERS)
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const [cursorHistory, setCursorHistory] = useState<(string | undefined)[]>([])

  const { data, isLoading, isError, error } = useTournaments(filters, cursor)

  function updateFilters(next: TournamentListFilters) {
    setFilters(next)
    setCursor(undefined)
    setCursorHistory([])
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
      <div className="flex flex-col gap-2">
        <Eyebrow>Duel Commander · Tournaments</Eyebrow>
        <CardTitle>Where the format gets decided.</CardTitle>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          Source
          <select
            className={inputClass}
            value={filters.source ?? ''}
            onChange={(e) => {
              const value = e.target.value
              updateFilters({
                ...filters,
                source:
                  value === '' ? undefined : (value as TournamentListFilters['source']),
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
      </div>

      {isLoading && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <Card className="border-destructive/40 text-destructive">
          Failed to load tournaments{error instanceof Error ? `: ${error.message}` : '.'}
        </Card>
      )}

      {data && (
        <>
          <Card className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Players</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.data.map((tournament) => (
                  <TableRow key={tournament.id}>
                    <TableCell>{tournament.date}</TableCell>
                    <TableCell>
                      <Link
                        to={`/tournaments/${tournament.id}`}
                        className="font-semibold text-foreground hover:text-accent"
                      >
                        {tournament.name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="accent">{tournament.source}</Badge>
                    </TableCell>
                    <TableCell>{tournament.players}</TableCell>
                  </TableRow>
                ))}
                {data.data.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground">
                      No tournaments match these filters.
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
