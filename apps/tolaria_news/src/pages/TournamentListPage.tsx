import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTournaments } from '@/hooks/useTournaments'
import { useTrendingCommanders } from '@/hooks/useCommanderTrends'
import { useStaples } from '@/hooks/useDecks'
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
import { CommanderTrendChart } from '@/components/commanderTrends/CommanderTrendChart'
import {
  TournamentWindowFilter,
  resolveWindowParams,
  type WindowPreset,
} from '@/components/commanderTrends/TournamentWindowFilter'
import { StaplesSection } from '@/components/staples-section'
import { TournamentSizeFilter } from '@/components/tournament-size-filter'

const SOURCES = [
  { value: '', label: 'All sources' },
  { value: 'mtgo', label: 'MTGO' },
  { value: 'mtgtop8', label: 'MTGTop8' },
] as const

const inputClass =
  'h-9 rounded-(--radius-input) border border-border bg-input px-2 text-sm text-foreground'

const DEFAULT_PRESET: WindowPreset = 'current_season'

export function TournamentListPage() {
  const [source, setSource] = useState<TournamentListFilters['source']>(undefined)
  const [sizes, setSizes] = useState<string[]>([])
  const [preset, setPreset] = useState<WindowPreset>(DEFAULT_PRESET)
  // Committed custom-range dates -- what actually drives the query. Kept
  // separate from the inputs' own draft value (see `draftDateFrom`/
  // `draftDateTo` below) so typing doesn't refetch on every keystroke.
  const [customDateFrom, setCustomDateFrom] = useState('')
  const [customDateTo, setCustomDateTo] = useState('')
  const [draftDateFrom, setDraftDateFrom] = useState('')
  const [draftDateTo, setDraftDateTo] = useState('')
  const [cursor, setCursor] = useState<string | undefined>(undefined)
  const [cursorHistory, setCursorHistory] = useState<(string | undefined)[]>([])

  const isAtDefaultFilters =
    source === undefined &&
    sizes.length === 0 &&
    preset === DEFAULT_PRESET &&
    customDateFrom === '' &&
    customDateTo === ''

  const windowParams = resolveWindowParams(preset, customDateFrom, customDateTo)
  const trending = useTrendingCommanders(
    windowParams.mode,
    windowParams.periodOffset,
    windowParams.dateFrom,
    windowParams.dateTo,
  )
  const resolvedWindow = trending.data?.data.window
  const staples = useStaples(
    resolvedWindow?.date_from,
    resolvedWindow?.date_to,
    undefined,
    resolvedWindow !== undefined,
  )

  // Tolaria News only covers Duel Commander (per apps/tolaria_news/README.md) —
  // format is fixed, not a user-facing filter. The date range comes from the
  // shared window filter above, not an independent From/To input.
  const filters: TournamentListFilters = {
    format: 'Duel Commander',
    source,
    sizes: sizes.length > 0 ? sizes : undefined,
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

  function resetFilters() {
    setSource(undefined)
    setSizes([])
    setPreset(DEFAULT_PRESET)
    setCustomDateFrom('')
    setCustomDateTo('')
    setDraftDateFrom('')
    setDraftDateTo('')
    resetPagination()
  }

  function commitDateFrom() {
    setCustomDateFrom(draftDateFrom)
    resetPagination()
  }

  function commitDateTo() {
    setCustomDateTo(draftDateTo)
    resetPagination()
  }

  function toggleSize(bucket: string) {
    setSizes((current) =>
      current.includes(bucket)
        ? current.filter((b) => b !== bucket)
        : [...current, bucket],
    )
    resetPagination()
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
          <Eyebrow>Duel Commander · Tournaments</Eyebrow>
          <CardTitle>Where the format gets decided.</CardTitle>
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

      <div className="flex flex-wrap items-center gap-3">
        <TournamentWindowFilter
          preset={preset}
          onPresetChange={(next) => {
            setPreset(next)
            setDraftDateFrom('')
            setDraftDateTo('')
            setCustomDateFrom('')
            setCustomDateTo('')
            resetPagination()
          }}
          customDateFrom={draftDateFrom}
          customDateTo={draftDateTo}
          onCustomDateFromChange={setDraftDateFrom}
          onCustomDateToChange={setDraftDateTo}
          onCustomDateFromCommit={commitDateFrom}
          onCustomDateToCommit={commitDateTo}
        />
        {(trending.isLoading || staples.isLoading) && (
          <span className="text-xs text-muted-foreground">Loading…</span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <CardTitle className="text-base">Top commanders</CardTitle>
        <CommanderTrendChart
          series={trending.data?.data.series}
          isLoading={trending.isLoading}
          isError={trending.isError}
        />
      </div>

      <div className="flex flex-col gap-2">
        <CardTitle className="text-base">Staples</CardTitle>
        <StaplesSection
          data={staples.data?.data}
          isLoading={staples.isLoading}
          isError={staples.isError}
        />
      </div>

      <p className="text-xs text-muted-foreground">
        Trends and staples are pooled across qualifying tournaments in the window above,
        see{' '}
        <Link to="/methodology" className="underline hover:text-accent">
          methodology
        </Link>{' '}
        for the pooling and threshold rules.
      </p>

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
        <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
          Tournament size
          <TournamentSizeFilter selected={sizes} onToggle={toggleSize} />
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
