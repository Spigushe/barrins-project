import { useState } from 'react'
import { useArchetypes } from '@/hooks/useKarnTablets'
import type { WindowMode } from '@/schemas/karnTablets'
import { WindowModeSelect } from '@/components/karnTablets/WindowModeSelect'
import { Card, CardTitle, CardDescription } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'

// PROVISIONAL page — see src/schemas/karnTablets.ts. Prepared ahead of T4
// iteration 2 / T6 ("Karn Tablets"), which hasn't shipped; only reachable
// behind VITE_FEATURE_KARN_TABLETS.
export function ArchetypesPage() {
  const [windowMode, setWindowMode] = useState<WindowMode>('rolling_30d')
  const { data, isLoading, isError } = useArchetypes(windowMode)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between gap-3">
        <div className="flex flex-col gap-2">
          <Eyebrow>Archetypes</Eyebrow>
          <CardTitle>Every archetype, traced to its core.</CardTitle>
          <CardDescription>Clustered Duel Commander deck archetypes.</CardDescription>
        </div>
        <WindowModeSelect value={windowMode} onChange={setWindowMode} />
      </div>

      {isLoading && <Skeleton className="h-40 w-full" />}

      {isError && (
        <Card className="border-destructive/40 text-destructive">
          Archetype data isn't available yet — this view is prepared ahead of the Karn
          Tablets backend (T4 iteration 2), which hasn't shipped.
        </Card>
      )}

      {data && (
        <Card className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Archetype</TableHead>
                <TableHead>Deck share</TableHead>
                <TableHead>Decks</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.data.map((archetype) => (
                <TableRow key={archetype.id}>
                  <TableCell>{archetype.name}</TableCell>
                  <TableCell>{(archetype.deck_share * 100).toFixed(1)}%</TableCell>
                  <TableCell>{archetype.deck_count}</TableCell>
                </TableRow>
              ))}
              {data.data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="text-center text-muted-foreground">
                    No archetypes for this window.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}
