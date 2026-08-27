import { useEffect, useState } from 'react'
import { useMetagame } from '@/hooks/useKarnTablets'
import type { WindowMode } from '@/schemas/karnTablets'
import { WindowModeSelect } from '@/components/karnTablets/WindowModeSelect'
import { WindowStepper } from '@/components/karnTablets/WindowStepper'
import { MetagameBarChart } from '@/components/karnTablets/MetagameBarChart'
import { CardTitle, CardDescription } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'

// PROVISIONAL page — see src/schemas/karnTablets.ts. Prepared ahead of T4
// iteration 2 / T6 ("Karn Tablets"); only reachable behind
// VITE_FEATURE_KARN_TABLETS.
export function MetagamePage() {
  const [windowMode, setWindowMode] = useState<WindowMode>('banlist_period')
  // `at` = a past window's label; `undefined` = the most recent window.
  const [at, setAt] = useState<string | undefined>(undefined)
  useEffect(() => {
    setAt(undefined)
  }, [windowMode])

  const { data, isLoading, isError } = useMetagame(windowMode, at)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-3">
        <div className="flex flex-col gap-2">
          <Eyebrow>Metagame</Eyebrow>
          <CardTitle>What&rsquo;s winning in Duel Commander.</CardTitle>
          <CardDescription>
            Archetype share of a clustering run, largest first, with each
            archetype&rsquo;s movement since the previous period.
          </CardDescription>
        </div>
        <WindowModeSelect value={windowMode} onChange={setWindowMode} />
      </div>

      {data && (
        <WindowStepper
          window={data.data.window}
          previousWindow={data.data.previous_window}
          nextWindow={data.data.next_window}
          onSelect={setAt}
        />
      )}

      <MetagameBarChart
        archetypes={data?.data.archetypes}
        isLoading={isLoading}
        isError={isError}
      />
    </div>
  )
}
