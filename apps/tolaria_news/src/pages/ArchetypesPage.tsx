import { useEffect, useState } from 'react'
import { useArchetypes } from '@/hooks/useKarnTablets'
import type { WindowMode } from '@/schemas/karnTablets'
import { WindowModeSelect } from '@/components/karnTablets/WindowModeSelect'
import { WindowStepper } from '@/components/karnTablets/WindowStepper'
import { ArchetypeDetailTable } from '@/components/karnTablets/ArchetypeDetailTable'
import { CardTitle, CardDescription } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
import { Button } from '@/components/ui/button'

// PROVISIONAL page — see src/schemas/karnTablets.ts. Prepared ahead of T4
// iteration 2 / T6 ("Karn Tablets"), which hasn't shipped; only reachable
// behind VITE_FEATURE_KARN_TABLETS.
export function ArchetypesPage() {
  const [windowMode, setWindowMode] = useState<WindowMode>('banlist_period')
  // `at` = a past window's label; `undefined` = the most recent window.
  const [at, setAt] = useState<string | undefined>(undefined)
  // Forward-only cursor history: one entry per visited page, `undefined`
  // for page 1. Reset whenever the window (kind or period) changes.
  const [cursors, setCursors] = useState<(string | undefined)[]>([undefined])
  useEffect(() => {
    setAt(undefined)
    setCursors([undefined])
  }, [windowMode])

  function stepWindow(label: string | undefined) {
    setAt(label)
    setCursors([undefined])
  }

  const currentCursor = cursors[cursors.length - 1]
  const { data, isLoading, isError } = useArchetypes(windowMode, at, currentCursor)

  const nextCursor = data?.page?.next_cursor ?? null
  const pageNumber = cursors.length

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-3">
        <div className="flex flex-col gap-2">
          <Eyebrow>Archetypes</Eyebrow>
          <CardTitle>Every archetype, traced to its core.</CardTitle>
          <CardDescription>
            Each clustered archetype&rsquo;s representative decklist size and its
            most-copied signature cards.
          </CardDescription>
        </div>
        <WindowModeSelect value={windowMode} onChange={setWindowMode} />
      </div>

      {data && (
        <WindowStepper
          window={data.data.window}
          previousWindow={data.data.previous_window}
          nextWindow={data.data.next_window}
          onSelect={stepWindow}
        />
      )}

      <ArchetypeDetailTable
        archetypes={data?.data.archetypes}
        isLoading={isLoading}
        isError={isError}
      />

      {(pageNumber > 1 || nextCursor) && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <Button
            variant="outline"
            disabled={pageNumber === 1}
            onClick={() => {
              setCursors((current) => current.slice(0, -1))
            }}
          >
            Previous
          </Button>
          <span className="font-mono">Page {pageNumber}</span>
          <Button
            variant="outline"
            disabled={!nextCursor}
            onClick={() => {
              if (nextCursor) setCursors((current) => [...current, nextCursor])
            }}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
