import { useActiveDeck } from '@/contexts/active-deck-context'
import { useArchetypeSummary, useMatchupSummary } from '@/hooks/useStats'
import {
  ARCHETYPE_BORDER_CLASS,
  ARCHETYPE_LABELS,
  ARCHETYPE_TEXT_CLASS,
  formatPercent,
  winrateTextClass,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Card, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const WINRATE_BANDS = [
  { label: 'Très positif (80-100%)', className: 'bg-winrate-80' },
  { label: 'Positif (60-79%)', className: 'bg-winrate-60' },
  { label: 'Équilibré (40-59%)', className: 'bg-winrate-40' },
  { label: 'Négatif (20-39%)', className: 'bg-winrate-20' },
  { label: 'Très négatif (0-19%)', className: 'bg-winrate-0' },
]

export function ArchetypeSummarySection() {
  const { data } = useArchetypeSummary()

  return (
    <Card>
      <CardTitle>Répartition par archétype</CardTitle>
      <div
        className="mt-3 grid gap-4"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}
      >
        {data?.map((summary) => (
          <div
            key={summary.category}
            className={cn(
              'rounded-(--radius-input) border-2 bg-input-inline p-4',
              ARCHETYPE_BORDER_CLASS[summary.category],
            )}
          >
            <div className="flex items-center justify-between">
              <h3
                className={cn(
                  'text-sm font-bold',
                  ARCHETYPE_TEXT_CLASS[summary.category],
                )}
              >
                {ARCHETYPE_LABELS[summary.category]}
              </h3>
              <span
                className={cn(
                  'font-mono text-sm font-semibold',
                  winrateTextClass(summary.average_winrate),
                )}
              >
                {formatPercent(summary.average_winrate)}
              </span>
            </div>
            <ul className="mt-3 flex flex-col gap-1.5">
              {summary.decks.map((deck) => (
                <li
                  key={deck.id}
                  className="flex items-center justify-between text-[13px]"
                >
                  <span className="text-foreground">{deck.name}</span>
                  <span className={cn('font-mono', winrateTextClass(deck.winrate))}>
                    {formatPercent(deck.winrate)}
                  </span>
                </li>
              ))}
              {summary.decks.length === 0 && (
                <li className="text-[12.5px] text-muted-foreground">Aucun deck.</li>
              )}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  )
}

export function MatchupSummarySection() {
  const { activeDeckId } = useActiveDeck()
  const { data } = useMatchupSummary(activeDeckId)

  return (
    <Card>
      <CardTitle>Synthèse des match-ups</CardTitle>
      <Table className="mt-3">
        <TableHeader>
          <TableRow>
            <TableHead>Vs. deck</TableHead>
            <TableHead>Winrate global</TableHead>
            <TableHead>Winrate OTP</TableHead>
            <TableHead>Winrate OTD</TableHead>
            <TableHead>V/D OTP</TableHead>
            <TableHead>V/D OTD</TableHead>
            <TableHead>Parties</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.rows.map((row) => (
            <TableRow key={row.opponent_deck_id}>
              <TableCell>{row.opponent_deck_name}</TableCell>
              <TableCell
                className={cn('font-mono', winrateTextClass(row.winrate_global))}
              >
                {formatPercent(row.winrate_global)}
              </TableCell>
              <TableCell className={cn('font-mono', winrateTextClass(row.winrate_otp))}>
                {formatPercent(row.winrate_otp)}
              </TableCell>
              <TableCell className={cn('font-mono', winrateTextClass(row.winrate_otd))}>
                {formatPercent(row.winrate_otd)}
              </TableCell>
              <TableCell className="font-mono">{row.ratio_otp}</TableCell>
              <TableCell className="font-mono">{row.ratio_otd}</TableCell>
              <TableCell className="font-mono">{row.match_count}</TableCell>
            </TableRow>
          ))}
          {(data?.rows.length ?? 0) === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground">
                Aucune donnée.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell>Winrate moyen</TableCell>
            <TableCell
              colSpan={6}
              className={cn('font-mono', winrateTextClass(data?.average_winrate ?? null))}
            >
              {formatPercent(data?.average_winrate ?? null)}
            </TableCell>
          </TableRow>
        </TableFooter>
      </Table>

      <div className="mt-3 flex flex-wrap gap-3 text-[11.5px] text-muted-foreground">
        {WINRATE_BANDS.map((band) => (
          <span key={band.label} className="flex items-center gap-1.5">
            <span className={cn('size-2.5 rounded-full', band.className)} />
            {band.label}
          </span>
        ))}
      </div>
    </Card>
  )
}
