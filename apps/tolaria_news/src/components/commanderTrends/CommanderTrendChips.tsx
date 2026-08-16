import { Line, LineChart, ResponsiveContainer } from 'recharts'
import { CommanderHoverBadge } from '@/components/commander-hover-badge'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { CommanderTrendSeries } from '@/schemas/tolariaNews'

function CommanderTrendChip({ series }: { series: CommanderTrendSeries }) {
  const data = series.points.map((point, index) => ({
    index,
    deck_count: point.deck_count,
  }))

  return (
    <Card className="flex w-56 flex-col gap-2 p-3">
      <div className="flex items-center justify-between gap-2">
        <CommanderHoverBadge commanders={series.commanders} />
        <span className="font-mono text-xs text-muted-foreground">
          {series.total_deck_count}
        </span>
      </div>
      <div className="h-8">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
            <Line
              type="monotone"
              dataKey="deck_count"
              stroke="var(--color-accent)"
              strokeWidth={1.5}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

/** Top-10 most-played commanders (or partner pairs) chip row, with a
 * per-commander play-count sparkline. Presentational -- the window/date
 * filter driving `series` is owned by `TournamentListPage` (shared with
 * the tournament table below it), not by this component. */
export function CommanderTrendChips({
  series,
  isLoading,
  isError,
}: {
  series: CommanderTrendSeries[] | undefined
  isLoading: boolean
  isError: boolean
}) {
  return (
    <div className="flex flex-col gap-3">
      {isLoading && (
        <div className="flex flex-wrap gap-3">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-24 w-56" />
          ))}
        </div>
      )}

      {isError && (
        <Card className="border-destructive/40 text-destructive">
          Failed to load trending commanders.
        </Card>
      )}

      {series && series.length === 0 && (
        <p className="text-sm text-muted-foreground">No decks recorded in this window.</p>
      )}

      {series && series.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {series.map((s) => (
            <CommanderTrendChip
              key={s.commanders.map((c) => c.name).join(' / ')}
              series={s}
            />
          ))}
        </div>
      )}
    </div>
  )
}
