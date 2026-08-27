import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { MomentumBadge } from './MomentumBadge'
import { ArchetypeName } from './ArchetypeName'
import type { Archetype } from '@/schemas/karnTablets'

const MAX_ROWS = 20

/** The latest clustering run's archetype-share distribution as a
 * horizontal bar chart, largest first, capped at the top 20. Each row
 * carries a rising / falling / stable / new chip comparing it to the
 * previous run (classified server-side). Presentational: the window-mode
 * filter driving `archetypes` is owned by `MetagamePage`.
 *
 * PROVISIONAL page — see src/schemas/karnTablets.ts. Reachable only behind
 * `VITE_FEATURE_KARN_TABLETS`. */
export function MetagameBarChart({
  archetypes,
  isLoading,
  isError,
}: {
  archetypes: Archetype[] | undefined
  isLoading: boolean
  isError: boolean
}) {
  if (isLoading) return <Skeleton className="h-96 w-full" />

  if (isError) {
    return (
      <Card className="border-destructive/40 text-destructive">
        Failed to load the metagame snapshot.
      </Card>
    )
  }

  if (!archetypes) return null

  if (archetypes.length === 0) {
    return <p className="text-sm text-muted-foreground">No archetypes for this window.</p>
  }

  // The backend already sorts largest-first; slice defensively and scale
  // every bar to the biggest share in the visible set.
  const rows = archetypes.slice(0, MAX_ROWS)
  const maxShare = Math.max(...rows.map((r) => r.deck_share))

  return (
    <Card>
      <ul className="flex flex-col gap-3" aria-label="Archetype share, largest first">
        {rows.map((archetype) => (
          <li key={archetype.id} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <span className="truncate text-sm font-medium" title={archetype.name}>
                  <ArchetypeName
                    name={archetype.name}
                    commanders={archetype.commanders}
                  />
                </span>
                <MomentumBadge
                  momentum={archetype.momentum}
                  deckShareDelta={archetype.deck_share_delta}
                />
              </div>
              <span className="flex-none font-mono text-xs tabular-nums text-muted-foreground">
                {(archetype.deck_share * 100).toFixed(1)}% · {archetype.deck_count}
              </span>
            </div>
            <div className="h-4 overflow-hidden rounded-(--radius-input) bg-input">
              <div
                className="h-full rounded-(--radius-input) bg-accent"
                style={{
                  width: `${Math.max(2, (archetype.deck_share / maxShare) * 100).toString()}%`,
                }}
              />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}
