import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ArchetypeName } from './ArchetypeName'
import type { Trend } from '@/schemas/karnTablets'

// Two rows of five on wider screens; fewer columns (more rows) as it
// narrows.
const MAX_FACETS = 10
const GRID_COLS = 'grid-cols-2 sm:grid-cols-3 md:grid-cols-5'
const VIEW_W = 210
const VIEW_H = 70

function pct(share: number): string {
  return `${(share * 100).toFixed(1)}%`
}

/** Split a point list into runs of consecutive non-null values, each as
 * `[x, y]` pairs — so a gap (an archetype with no cluster that run) breaks
 * the line instead of diving to zero. */
function segments(
  shares: (number | null)[],
  x: (i: number) => number,
  y: (v: number) => number,
): [number, number][][] {
  const out: [number, number][][] = []
  let current: [number, number][] = []
  shares.forEach((share, i) => {
    if (share == null) {
      if (current.length > 0) out.push(current)
      current = []
    } else {
      current.push([x(i), y(share)])
    }
  })
  if (current.length > 0) out.push(current)
  return out
}

function linePath(segs: [number, number][][]): string {
  return segs
    .map((seg) => `M${seg.map(([px, py]) => `${px},${py}`).join(' L')}`)
    .join(' ')
}

function areaPath(seg: [number, number][] | undefined): string {
  if (!seg || seg.length < 2) return ''
  const start = seg[0][0]
  const end = seg[seg.length - 1][0]
  return `M${start},${VIEW_H} L${seg.map(([px, py]) => `${px},${py}`).join(' L')} L${end},${VIEW_H} Z`
}

function monthLabel(isoDate: string): string {
  return isoDate.slice(0, 7)
}

/** One area sparkline per archetype, tracking its deck share across the
 * recent runs of the selected window mode — a small-multiples alternative
 * to the shared-axis line chart above it. Deliberately provisional: kept
 * as a second block on the Trends page until a single display method is
 * chosen. Presentational: the window-mode filter driving `trends` is owned
 * by `TrendsPage`.
 *
 * PROVISIONAL page — see src/schemas/karnTablets.ts. */
export function ArchetypeFacetGrid({
  trends,
  isLoading,
  isError,
}: {
  trends: Trend[] | undefined
  isLoading: boolean
  isError: boolean
}) {
  if (isLoading) return <Skeleton className="h-64 w-full" />

  if (isError) {
    return (
      <Card className="border-destructive/40 text-destructive">
        Failed to load archetype trends.
      </Card>
    )
  }

  if (!trends) return null

  const facets = trends.slice(0, MAX_FACETS)
  const withEnoughPoints = facets.filter((t) => t.points.length >= 2)

  if (withEnoughPoints.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Not enough runs yet to chart per-archetype movement.
      </p>
    )
  }

  const pointCount = withEnoughPoints[0].points.length
  const allShares = withEnoughPoints.flatMap((t) =>
    t.points.map((p) => p.deck_share).filter((v): v is number => v != null),
  )
  const yMax = Math.max(...allShares, 0.05)

  const x = (i: number) => (i / (pointCount - 1)) * VIEW_W
  const y = (v: number) => VIEW_H - (v / yMax) * VIEW_H

  const first = withEnoughPoints[0].points[0]
  const last = withEnoughPoints[0].points[pointCount - 1]

  return (
    <div className="flex flex-col gap-2">
      <div
        className={`grid ${GRID_COLS} gap-px overflow-hidden rounded-(--radius-card) border border-border bg-border`}
      >
        {withEnoughPoints.map((trend) => {
          const shares = trend.points.map((p) => p.deck_share)
          const present = shares.filter((v) => v != null).length
          const nonNull = shares.filter((v): v is number => v != null)
          const peak = nonNull.length > 0 ? Math.max(...nonNull) : 0
          const latest = [...shares].reverse().find((v) => v != null) ?? null
          const segs = segments(shares, x, y)
          const end = segs.at(-1)?.at(-1)

          return (
            <div key={trend.archetype_id} className="bg-card p-3">
              <div className="truncate font-serif text-sm" title={trend.archetype_name}>
                <ArchetypeName
                  name={trend.archetype_name}
                  commanders={trend.commanders}
                />
              </div>
              <div className="mb-1 font-mono text-[10px] text-muted-foreground">
                {present}/{pointCount} periods · peak {pct(peak)} · latest{' '}
                {latest != null ? pct(latest) : '—'}
              </div>
              <svg
                viewBox={`0 0 ${VIEW_W.toString()} ${VIEW_H.toString()}`}
                preserveAspectRatio="none"
                className="block h-[70px] w-full overflow-visible"
                role="img"
                aria-label={`${trend.archetype_name}: deck share across ${pointCount.toString()} periods`}
              >
                <line
                  x1="0"
                  y1={VIEW_H}
                  x2={VIEW_W}
                  y2={VIEW_H}
                  stroke="var(--color-border)"
                  strokeWidth="1"
                />
                {areaPath(segs[0]) && (
                  <path
                    d={areaPath(segs[0])}
                    fill="var(--color-accent)"
                    fillOpacity="0.14"
                  />
                )}
                <path
                  d={linePath(segs)}
                  fill="none"
                  stroke="var(--color-accent)"
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
                {end && (
                  <circle
                    cx={end[0]}
                    cy={end[1]}
                    r="3"
                    fill="var(--color-accent)"
                    stroke="var(--color-card)"
                    strokeWidth="2"
                  />
                )}
              </svg>
            </div>
          )
        })}
      </div>
      <div className="flex justify-between px-1 font-mono text-[10px] text-muted-foreground">
        <span>◀ {monthLabel(first.window.date_from)}</span>
        <span>{monthLabel(last.window.date_to)} ▶</span>
      </div>
    </div>
  )
}
