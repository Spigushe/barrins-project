import { Fragment } from 'react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { CardNameCell } from '@/components/card-name-cell'
import { ArchetypeName } from './ArchetypeName'
import type { MetagameArchetypeDetail, RepresentativeCard } from '@/schemas/karnTablets'

const SIGNATURE_COUNT = 6

/** Distinct-card count / total-card count of a representative mainboard. */
function repListSize(cards: RepresentativeCard[]): { distinct: number; total: number } {
  return {
    distinct: cards.length,
    total: cards.reduce((sum, card) => sum + card.qty, 0),
  }
}

/** Top cards by copy count that the backend flagged `is_signature`
 * (non-lands, plus lands that aren't metagame-wide staples). */
function signatureCards(cards: RepresentativeCard[]): RepresentativeCard[] {
  return cards.filter((card) => card.is_signature).slice(0, SIGNATURE_COUNT)
}

/** The full cluster list behind the bar chart, with the representative
 * decklist's size and its most-copied signature cards (each hoverable for
 * Scryfall art). Presentational: `ArchetypesPage` owns the window-mode
 * filter and pagination.
 *
 * PROVISIONAL page — see src/schemas/karnTablets.ts. */
export function ArchetypeDetailTable({
  archetypes,
  isLoading,
  isError,
}: {
  archetypes: MetagameArchetypeDetail[] | undefined
  isLoading: boolean
  isError: boolean
}) {
  if (isLoading) return <Skeleton className="h-64 w-full" />

  if (isError) {
    return (
      <Card className="border-destructive/40 text-destructive">
        Failed to load archetype detail.
      </Card>
    )
  }

  if (!archetypes) return null

  const maxShare =
    archetypes.length > 0 ? Math.max(...archetypes.map((a) => a.deck_share)) : 0

  return (
    <Card className="p-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Archetype</TableHead>
            <TableHead className="text-right">Decks</TableHead>
            <TableHead>Share</TableHead>
            <TableHead className="text-right">Rep. list</TableHead>
            <TableHead>Signature cards</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {archetypes.map((archetype) => {
            const size = repListSize(archetype.representative_mainboard)
            const signature = signatureCards(archetype.representative_mainboard)
            return (
              <TableRow key={archetype.id}>
                <TableCell className="font-medium">
                  <ArchetypeName
                    name={archetype.name}
                    commanders={archetype.commanders}
                  />
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums">
                  {archetype.deck_count}
                </TableCell>
                <TableCell>
                  <span className="flex items-center gap-2">
                    <span className="font-mono text-xs tabular-nums text-muted-foreground">
                      {(archetype.deck_share * 100).toFixed(1)}%
                    </span>
                    <span
                      aria-hidden="true"
                      className="inline-block h-2 rounded-(--radius-pill) bg-accent"
                      style={{
                        width: `${(maxShare > 0
                          ? (archetype.deck_share / maxShare) * 64
                          : 0
                        ).toString()}px`,
                      }}
                    />
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums text-muted-foreground">
                  {size.distinct}/{size.total}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {signature.length > 0
                    ? signature.map((card, index) => (
                        <Fragment key={card.name}>
                          {index > 0 && ', '}
                          <CardNameCell
                            card={{ name: card.name, scryfall_id: card.scryfall_id }}
                          />
                        </Fragment>
                      ))
                    : '—'}
                </TableCell>
              </TableRow>
            )
          })}
          {archetypes.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                No archetypes for this window.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Card>
  )
}
