import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { usePlatformMetrics, usePlatformMetricsTimeseries } from '@/hooks/useAdmin'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { MetricTimeseries, MetricTimeseriesPoint } from '@/schemas/tamiyoScroll'

const STAT_TILES: {
  key: 'total_accounts' | 'total_personal_decks' | 'total_matches'
  label: string
}[] = [
  { key: 'total_accounts', label: 'Accounts created' },
  { key: 'total_personal_decks', label: 'Personal decks created' },
  { key: 'total_matches', label: 'Matches recorded' },
]

type Granularity = 'daily' | 'weekly' | 'monthly'

const GRANULARITY_DESCRIPTIONS: Record<Granularity, string> = {
  daily: 'Day-by-day evolution',
  weekly: 'Week-by-week evolution',
  monthly: 'Month-by-month evolution',
}

// One chart color per metric, reusing existing themed CSS variables
// (`index.css`) instead of introducing new hard-coded colors.
const METRIC_CHARTS: {
  key: 'accounts' | 'personal_decks' | 'matches'
  label: string
  color: string
}[] = [
  { key: 'accounts', label: 'New accounts', color: 'var(--color-accent)' },
  { key: 'personal_decks', label: 'New personal decks', color: 'var(--color-owner)' },
  { key: 'matches', label: 'New matches', color: 'var(--color-tournament)' },
]

function formatPeriodLabel(periodStart: string, granularity: Granularity): string {
  const d = new Date(periodStart)
  if (Number.isNaN(d.getTime())) return periodStart
  if (granularity === 'monthly') {
    return d.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
  }
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function bucketsFor(
  metric: MetricTimeseries | undefined,
  granularity: Granularity,
): MetricTimeseriesPoint[] {
  return metric?.[granularity] ?? []
}

/** One metric's day/week/month evolution as a single line chart, switched
 * via the shared `granularity` tab above it (S6, added 2026-08-02 —
 * `recharts`, see the S6 doc's "Added requirement" section for why a
 * charting dependency was introduced here). */
function MetricTimeseriesChart({
  label,
  color,
  metric,
  granularity,
}: {
  label: string
  color: string
  metric: MetricTimeseries | undefined
  granularity: Granularity
}) {
  const points = bucketsFor(metric, granularity)
  const data = points.map((p) => ({
    period_start: p.period_start,
    label: formatPeriodLabel(p.period_start, granularity),
    count: p.count,
  }))

  return (
    <Card>
      <CardTitle>{label}</CardTitle>
      <CardDescription>{GRANULARITY_DESCRIPTIONS[granularity]}</CardDescription>
      <div className="mt-3 h-55">
        {data.length === 0 ? (
          <p className="text-sm text-muted-foreground">No data in this window yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: 'var(--color-muted-foreground)' }}
                stroke="var(--color-border)"
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11, fill: 'var(--color-muted-foreground)' }}
                stroke="var(--color-border)"
                width={32}
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
              <Line
                type="monotone"
                dataKey="count"
                stroke={color}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  )
}

/** Admin-only usage/metrics dashboard (S6). The three v2.0.0 staged
 * adoption signals as flat all-time totals (tiles), plus their
 * day/week/month time-comparison (added 2026-08-02, see
 * docs/project/v2.0.0-bump/s6-admin-metrics-dashboard/index.md). */
export function AdminMetricsPage() {
  const { data, isLoading, isError } = usePlatformMetrics()
  const {
    data: timeseries,
    isLoading: isTimeseriesLoading,
    isError: isTimeseriesError,
  } = usePlatformMetricsTimeseries()
  const [granularity, setGranularity] = useState<Granularity>('daily')

  return (
    <div className="mx-auto max-w-[900px] px-8 pt-7 pb-20">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-extrabold text-foreground">Usage metrics</h1>
          <p className="text-[13px] text-muted-foreground">
            Admin only · aggregate counts
          </p>
        </div>
        <Link to="/tracker" className="text-sm text-muted-foreground hover:underline">
          Back to app
        </Link>
      </header>

      <div
        className="mt-6 grid gap-4"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {isError && (
          <p className="text-sm text-destructive">Could not load usage metrics.</p>
        )}
        {data &&
          STAT_TILES.map((tile) => (
            <Card key={tile.key}>
              <CardTitle>{data[tile.key].value.toLocaleString()}</CardTitle>
              <CardDescription>{tile.label}</CardDescription>
            </Card>
          ))}
      </div>

      <section className="mt-8">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-base font-bold text-foreground">Evolution over time</h2>
          <Tabs
            value={granularity}
            onValueChange={(value) => setGranularity(value as Granularity)}
          >
            <TabsList>
              <TabsTrigger value="daily">Day</TabsTrigger>
              <TabsTrigger value="weekly">Week</TabsTrigger>
              <TabsTrigger value="monthly">Month</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {isTimeseriesLoading && (
          <p className="mt-4 text-sm text-muted-foreground">Loading…</p>
        )}
        {isTimeseriesError && (
          <p className="mt-4 text-sm text-destructive">
            Could not load the time-comparison charts.
          </p>
        )}

        {timeseries && (
          <div
            className="mt-4 grid gap-4"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}
          >
            {METRIC_CHARTS.map((chart) => (
              <MetricTimeseriesChart
                key={chart.key}
                label={chart.label}
                color={chart.color}
                metric={timeseries[chart.key]}
                granularity={granularity}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
