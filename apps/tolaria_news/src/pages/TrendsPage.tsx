import { useState } from 'react'
import { useTrends } from '@/hooks/useKarnTablets'
import type { WindowMode } from '@/schemas/karnTablets'
import { WindowModeSelect } from '@/components/karnTablets/WindowModeSelect'
import { ArchetypeTrendChart } from '@/components/karnTablets/ArchetypeTrendChart'
import { ArchetypeFacetGrid } from '@/components/karnTablets/ArchetypeFacetGrid'
import { CardTitle, CardDescription } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'

// PROVISIONAL page — see src/schemas/karnTablets.ts. Prepared ahead of T4
// iteration 2 / T6 ("Karn Tablets"); only reachable behind
// VITE_FEATURE_KARN_TABLETS.
export function TrendsPage() {
  const [windowMode, setWindowMode] = useState<WindowMode>('banlist_period')
  const { data, isLoading, isError } = useTrends(windowMode)

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4">
        <div className="flex items-end justify-between gap-3">
          <div className="flex flex-col gap-2">
            <Eyebrow>Research · Trends</Eyebrow>
            <CardTitle>The metagame, over time.</CardTitle>
            <CardDescription>
              Every archetype&rsquo;s deck share across recent windows.
            </CardDescription>
          </div>
          <WindowModeSelect value={windowMode} onChange={setWindowMode} />
        </div>

        <ArchetypeTrendChart
          trends={data?.data}
          isLoading={isLoading}
          isError={isError}
        />
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <CardTitle className="text-xl">Per archetype, one panel each.</CardTitle>
          <CardDescription>
            The same data as a small-multiples grid — a provisional second view kept until
            we settle on one display method.
          </CardDescription>
        </div>

        <ArchetypeFacetGrid trends={data?.data} isLoading={isLoading} isError={isError} />
      </div>
    </div>
  )
}
