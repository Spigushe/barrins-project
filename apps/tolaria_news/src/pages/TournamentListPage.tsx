import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTournaments } from '@/hooks/useTournaments'
import { useTrendingCommanders } from '@/hooks/useCommanderTrends'
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
import { CommanderTrendChips } from '@/components/commanderTrends/CommanderTrendChips'
import {
  TournamentWindowFilter,
  resolveWindowParams,
  type WindowPreset,
} from '@/components/commanderTrends/TournamentWindowFilter'

const SOURCES = [
  { value: '', label: 'All sources' },
  { value: 'mtgo', label: 'MTGO' },
  { value: 'mtgtop8', label: 'MTGTop8' },
] as const

const inputClass =
  'h-9 rounded-(--radius-input) border border-border bg-input px-2 text-sm text-foreground'

export function TournamentListPage() {
  const [source, setSource] = useState<TournamentListFilters['source']>(undefined)
  const [preset, setPreset] = useState<WindowPreset>('current_season')
  const [customDateFrom, setCustomDateFrom] = useState('')
  const [customDateTo, setCustomDateTo] = useState('')
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const [cursorHistory, setCursorHistory] = useState<(string | undefined)[]>([])

  const windowParams = resolveWindowParams(preset, customDateFrom, customDateTo)
  const trending = useTrendingCommanders(
    windowParams.mode,
    windowParams.periodOffset,
    windowParams.dateFrom,
    windowParams.dateTo,
  )
  const resolvedWindow = trending.data?.data.window

  // Tolaria News only covers Duel Commander (per apps/tolaria_news/README.md) —
  // format is fixed, not a user-facing filter. The date range comes from the
  // shared window filter above, not an independent From/To input.
  const filters: TournamentListFilters = {
    format: 'Duel Commander',
    source,
    dateFrom: resolvedWindow?.date_from,
    dateTo: resolvedWindow?.date_to,
  }

  const { data, isLoading, isError, error } = useTournaments(
    filters,
    cursor,
    resolvedWindow !== undefined,
  )

  function resetPagination() {
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

      <TournamentWindowFilter
        preset={preset}
        onPresetChange={(next) => {
          setPreset(next)
          resetPagination()
        }}
        customDateFrom={customDateFrom}
        customDateTo={customDateTo}
        onCustomDateFromChange={(value) => {
          setCustomDateFrom(value)
          resetPagination()
        }}
        onCustomDateToChange={(value) => {
          setCustomDateTo(value)
          resetPagination()
        }}
      />

      <CommanderTrendChips
        series={trending.data?.data.series}
        isLoading={trending.isLoading}
        isError={trending.isError}
      />

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          Source
          <select
            className={inputClass}
            value={source ?? ''}
            onChange={(e) => {
              const value = e.target.value
              setSource(
                value === '' ? undefined : (value as TournamentListFilters['source']),
              )
              resetPagination()
            }}
          >
            {SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {(isLoading || resolvedWindow === undefined) && (
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

      {data && resolvedWindow !== undefined && (
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
