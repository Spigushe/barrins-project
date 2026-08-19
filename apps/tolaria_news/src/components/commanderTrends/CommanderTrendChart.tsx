import { useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { CommanderTrendSeries } from '@/schemas/tolariaNews'

/** Categorical chart palette -- 10 series, built for this app's Midnight
 * background (`--color-background: #0b1220`). Plain hex constants, not
 * Tailwind `@theme` CSS variables: a `--chart-1`..`--chart-10` (and,
 * renamed, `--color-chart-1`..`--color-chart-10`) numeric scale placed
 * in `@theme` was silently pruned by Tailwind v4's theme compiler down
 * to just its first and last entries in the generated `:root` block --
 * 8 of 10 series resolved `var(--chart-N)` to nothing and rendered with
 * `stroke: none`, invisible despite real, non-null data. Nothing here
 * needs a Tailwind utility class from these values (no `bg-chart-3`
 * anywhere) -- they're only ever consumed via this array, so a plain TS
 * constant is the one source of truth instead. Ordered so the first 3-4
 * are the most distinct -- used in order, one per series, up to the
 * top-10 commander cap this chart already has. */
const CHART_PALETTE = [
  '#7be0d6',
  '#c7a455',
  '#8fa8ff',
  '#e08a6a',
  '#a8d46f',
  '#d986c4',
  '#5fb4d8',
  '#e5c978',
  '#9c8fe0',
  '#6fcfa8',
]

function seriesLabel(series: CommanderTrendSeries): string {
  const names = series.commanders.map((c) => c.name).join(' / ')
  return `${names} (${series.total_deck_count.toString()})`
}

function seriesStroke(index: number): string {
  return CHART_PALETTE[index % CHART_PALETTE.length]
}

/** Top-10 most-played commanders (or partner pairs), as one line chart
 * with a legend rather than 10 separate sparkline cards -- lets trends
 * be compared directly against a shared axis instead of eyeballing
 * across cards. Presentational -- the window/date filter driving
 * `series` is owned by `TournamentListPage` (shared with the tournament
 * table below it), not by this component. */
export function CommanderTrendChart({
  series,
  isLoading,
  isError,
}: {
  series: CommanderTrendSeries[] | undefined
  isLoading: boolean
  isError: boolean
}) {
  // Which series the user has clicked off via the legend. Keyed by index
  // rather than label -- labels embed a deck count that's stable per
  // render but not a meaningful identity key across window changes.
  const [hiddenIndices, setHiddenIndices] = useState<Set<number>>(new Set())

  function toggleSeries(index: number) {
    setHiddenIndices((current) => {
      const next = new Set(current)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  if (isLoading) return <Skeleton className="h-80 w-full" />

  if (isError) {
    return (
      <Card className="border-destructive/40 text-destructive">
        Failed to load trending commanders.
      </Card>
    )
  }

  if (!series) return null

  if (series.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No decks recorded in this window.</p>
    )
  }

  const buckets = new Map<string, string>()
  series.forEach((trend) => {
    trend.points.forEach((point) => {
      buckets.set(`${point.date_from}:${point.date_to}`, point.date_to)
    })
  })

  const data = [...buckets].map(([bucketKey, label]) => {
    const row: Record<string, number | string | null> = { label }
    series.forEach((trend, seriesIndex) => {
      const point = trend.points.find(
        (candidate) => `${candidate.date_from}:${candidate.date_to}` === bucketKey,
      )
      // A 0-deck bucket drawn as a real point drags the line flat along
      // the x-axis for every bucket before a commander shows up -- with
      // 10 series sharing one y-axis, that flat run reads as "no line at
      // all" until the one bucket where it spikes. Treat 0 the same as a
      // missing bucket (null) so `connectNulls={false}` breaks the line
      // instead of drawing it, leaving only the commander's actual active
      // window visible.
      row[`series_${seriesIndex.toString()}`] = point?.deck_count ? point.deck_count : null
    })
    return row
  })

  return (
    <Card className="h-96 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="var(--color-border)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: 'var(--color-muted-foreground)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--color-border)' }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: 'var(--color-muted-foreground)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--color-border)' }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--color-card)',
              border: '1px solid var(--color-border)',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: 'var(--color-foreground)' }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11 }}
            // recharts' default Legend derives its payload from the <Line>
            // children, and that inference proved unreliable here (legend
            // order didn't match the series' rank order, and most entries
            // rendered with no color icon at all) -- the public component
            // doesn't accept a `payload` override either, so `content`
            // renders the legend directly from `series` instead, using the
            // exact same `seriesStroke(index)` each `<Line>` draws with.
            content={() => (
              <ul className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1">
                {series.map((s, index) => {
                  const hidden = hiddenIndices.has(index)
                  return (
                    <li key={seriesLabel(s)}>
                      <button
                        type="button"
                        onClick={() => {
                          toggleSeries(index)
                        }}
                        className="flex items-center gap-1.5"
                        style={{ opacity: hidden ? 0.4 : 1 }}
                        aria-pressed={!hidden}
                        title={hidden ? 'Hidden -- click to show' : 'Click to hide'}
                      >
                        <span
                          aria-hidden="true"
                          className="inline-block h-0.5 w-3"
                          style={{ backgroundColor: seriesStroke(index) }}
                        />
                        <span
                          style={{
                            color: 'var(--color-muted-foreground)',
                            textDecoration: hidden ? 'line-through' : 'none',
                          }}
                        >
                          {seriesLabel(s)}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          />
          {series.map(
            (s, index) =>
              !hiddenIndices.has(index) && (
                <Line
                  key={seriesLabel(s)}
                  type="monotone"
                  dataKey={`series_${index.toString()}`}
                  name={seriesLabel(s)}
                  stroke={seriesStroke(index)}
                  strokeWidth={2}
                  dot={false}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              ),
          )}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}
