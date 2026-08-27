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
import { seriesStroke } from '@/lib/chartPalette'
import { ArchetypeName } from './ArchetypeName'
import type { Trend } from '@/schemas/karnTablets'

/**
 * Every clustered archetype's deck share plotted as one shared-axis line
 * chart -- one line per archetype, chronological across the recent runs of
 * the selected window mode -- rather than a stack of per-archetype cards,
 * so movements can be compared directly. Presentational: the window-mode
 * filter driving `trends` is owned by `TrendsPage`.
 *
 * PROVISIONAL page -- see src/schemas/karnTablets.ts. Reachable only
 * behind `VITE_FEATURE_KARN_TABLETS`.
 */
export function ArchetypeTrendChart({
  trends,
  isLoading,
  isError,
}: {
  trends: Trend[] | undefined
  isLoading: boolean
  isError: boolean
}) {
  // Which archetypes the user has clicked off in the legend, keyed by the
  // index into `trends` (stable per render; archetype_id would also work
  // but index keeps this identical to CommanderTrendChart).
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

  if (isLoading) return <Skeleton className="h-96 w-full" />

  if (isError) {
    return (
      <Card className="border-destructive/40 text-destructive">
        Failed to load archetype trends.
      </Card>
    )
  }

  if (!trends) return null

  if (trends.length === 0) {
    return <p className="text-sm text-muted-foreground">No trend data for this window.</p>
  }

  // Union of every window bucket any archetype has a point for, oldest
  // first -- the backend returns points newest-first per series, so this
  // has to sort rather than trust order.
  const buckets = new Map<string, { from: string; to: string }>()
  trends.forEach((trend) => {
    trend.points.forEach((point) => {
      const key = `${point.window.date_from}:${point.window.date_to}`
      buckets.set(key, { from: point.window.date_from, to: point.window.date_to })
    })
  })
  const orderedBuckets = [...buckets.entries()].sort(([, a], [, b]) =>
    a.to.localeCompare(b.to),
  )

  const data = orderedBuckets.map(([bucketKey, bucket]) => {
    const row: Record<string, number | string | null> = { label: bucket.to }
    trends.forEach((trend, seriesIndex) => {
      const point = trend.points.find(
        (candidate) =>
          `${candidate.window.date_from}:${candidate.window.date_to}` === bucketKey,
      )
      // `deck_share` is 0..1 from the backend; a missing bucket or an
      // explicit null (no cluster that run) becomes null so
      // `connectNulls={false}` draws a gap instead of a dive to zero.
      row[`series_${seriesIndex.toString()}`] =
        point && point.deck_share !== null ? point.deck_share * 100 : null
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
            domain={[0, 'auto']}
            tickFormatter={(value: number) => `${value.toString()}%`}
            tick={{ fill: 'var(--color-muted-foreground)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--color-border)' }}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => `${Number(value).toFixed(1)}%`}
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
            // Same reasoning as CommanderTrendChart: recharts' inferred
            // legend proved unreliable (wrong order, missing color icons),
            // and the public component takes no `payload` override -- so
            // render it directly from `trends` with the same
            // `seriesStroke(index)` each `<Line>` uses.
            content={() => (
              <ul className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1">
                {trends.map((trend, index) => {
                  const hidden = hiddenIndices.has(index)
                  return (
                    <li key={trend.archetype_id}>
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
                          <ArchetypeName
                            name={trend.archetype_name}
                            commanders={trend.commanders}
                          />
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          />
          {trends.map(
            (trend, index) =>
              !hiddenIndices.has(index) && (
                <Line
                  key={trend.archetype_id}
                  type="monotone"
                  dataKey={`series_${index.toString()}`}
                  name={trend.archetype_name}
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
