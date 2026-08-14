import { useState } from 'react'
import { useTrends } from '@/hooks/useKarnTablets'
import type { WindowMode } from '@/schemas/karnTablets'
import { WindowModeSelect } from '@/components/karnTablets/WindowModeSelect'
import { Card, CardTitle, CardDescription } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
import { Skeleton } from '@/components/ui/skeleton'

// PROVISIONAL page — see src/schemas/karnTablets.ts. Prepared ahead of T4
// iteration 2 / T6 ("Karn Tablets"), which hasn't shipped; only reachable
// behind VITE_FEATURE_KARN_TABLETS.
export function TrendsPage() {
  const [windowMode, setWindowMode] = useState<WindowMode>('rolling_30d')
  const { data, isLoading, isError } = useTrends(windowMode)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-3">
        <div className="flex flex-col gap-2">
          <Eyebrow>Research · Trends</Eyebrow>
          <CardTitle>The metagame, over time.</CardTitle>
          <CardDescription>Archetype share over time, across windows.</CardDescription>
        </div>
        <WindowModeSelect value={windowMode} onChange={setWindowMode} />
      </div>

      {isLoading && <Skeleton className="h-40 w-full" />}

      {isError && (
        <Card className="border-destructive/40 text-destructive">
          Trend data isn't available yet — this view is prepared ahead of the Karn Tablets
          backend (T4 iteration 2), which hasn't shipped.
        </Card>
      )}

      {data && (
        <div className="flex flex-col gap-3">
          {data.data.map((trend) => (
            <Card key={trend.archetype_id}>
              <CardTitle className="text-sm">{trend.archetype_name}</CardTitle>
              <ul className="mt-2 flex flex-col gap-1 text-sm text-muted-foreground">
                {trend.points.map((point) => (
                  <li key={point.window.label}>
                    {point.window.label}: {(point.deck_share * 100).toFixed(1)}%
                  </li>
                ))}
              </ul>
            </Card>
          ))}
          {data.data.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No trend data for this window.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
