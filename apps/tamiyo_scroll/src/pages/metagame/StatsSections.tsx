import { useActiveDeck } from '@/contexts/active-deck-context'
import { useLocalStorageFlag } from '@/hooks/useLocalStorageFlag'
import { useArchetypeSummary, useMatchupSummary } from '@/hooks/useStats'
import {
  DISPLAY_PREF_MATCHUP_RESULT_FORMAT_2W0L,
  DISPLAY_PREF_MATCHUP_ROW_TINT,
} from '@/lib/displayPrefs'
import {
  ARCHETYPE_BORDER_CLASS,
  ARCHETYPE_LABELS,
  ARCHETYPE_TEXT_CLASS,
  formatMatchRatio,
  formatPercent,
  winrateRowTintClass,
  winrateTextClass,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
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
  { label: 'Very positive (80-100%)', className: 'bg-winrate-80' },
  { label: 'Positive (60-79%)', className: 'bg-winrate-60' },
  { label: 'Balanced (40-59%)', className: 'bg-winrate-40' },
  { label: 'Negative (20-39%)', className: 'bg-winrate-20' },
  { label: 'Very negative (0-19%)', className: 'bg-winrate-0' },
]

export function ArchetypeSummarySection() {
  const { activeDeckId } = useActiveDeck()
  const { data } = useArchetypeSummary(activeDeckId)

  return (
    <Card>
      <CardTitle>Breakdown by archetype</CardTitle>
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
                  className="flex items-center justify-between gap-2 text-[13px]"
                >
                  <span className="text-foreground">{deck.name}</span>
                  <span className="flex items-center gap-2">
                    {deck.is_readonly && <Badge variant="shared">shared</Badge>}
                    {!deck.is_readonly && deck.has_shared_data && (
                      <Badge variant="shared">w/ shared</Badge>
                    )}
                    <span className={cn('font-mono', winrateTextClass(deck.winrate))}>
                      {formatPercent(deck.winrate)}
                    </span>
                  </span>
                </li>
              ))}
              {summary.decks.length === 0 && (
                <li className="text-[12.5px] text-muted-foreground">No deck.</li>
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
  // S12 item 8 (default on) and item 9 (default off) — see
  // `AccountSettingsDialog`'s "Display" section for the toggle UI.
  const [rowTintEnabled] = useLocalStorageFlag(DISPLAY_PREF_MATCHUP_ROW_TINT, true)
  const [resultFormat2w0lEnabled] = useLocalStorageFlag(
    DISPLAY_PREF_MATCHUP_RESULT_FORMAT_2W0L,
    false,
  )

  return (
    <Card>
      {/* S12 item 6: legend moved above the table, inline with the title
          (right-aligned) so the reader knows what the colors mean before
          hitting the colored cells, without adding an extra stacked row. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CardTitle>Match-up summary</CardTitle>
        <div className="flex flex-wrap justify-end gap-3 text-[11.5px] text-muted-foreground">
          {WINRATE_BANDS.map((band) => (
            <span key={band.label} className="flex items-center gap-1.5">
              <span className={cn('size-2.5 rounded-full', band.className)} />
              {band.label}
            </span>
          ))}
        </div>
      </div>

      <Table className="mt-3">
        <TableHeader>
          <TableRow>
            <TableHead>Vs. deck</TableHead>
            {/* S12 item 5: the six non-"Vs. deck" columns share an equal,
                narrow width (7% each, 42% total — under the 45% cap),
                leaving "Vs. deck" unconstrained to absorb the rest. */}
            <TableHead className="w-[7%]">Winrate</TableHead>
            <TableHead className="w-[7%]">OTP</TableHead>
            <TableHead className="w-[7%]">OTD</TableHead>
            <TableHead className="w-[7%]">W/L OTP</TableHead>
            <TableHead className="w-[7%]">W/L OTD</TableHead>
            <TableHead className="w-[7%]">Matches</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data?.rows.map((row) => (
            <TableRow
              key={row.opponent_deck_id}
              className={rowTintEnabled ? winrateRowTintClass(row.winrate_global) : undefined}
            >
              <TableCell>
                <span className="flex items-center gap-2">
                  {row.opponent_deck_name}
                  {row.is_readonly && <Badge variant="shared">shared</Badge>}
                  {!row.is_readonly && row.has_shared_data && (
                    <Badge variant="shared">w/ shared</Badge>
                  )}
                </span>
              </TableCell>
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
              <TableCell className="font-mono text-muted-foreground">
                {formatMatchRatio(row.ratio_otp, resultFormat2w0lEnabled)}
              </TableCell>
              <TableCell className="font-mono text-muted-foreground">
                {formatMatchRatio(row.ratio_otd, resultFormat2w0lEnabled)}
              </TableCell>
              <TableCell className="font-mono">{row.match_count}</TableCell>
            </TableRow>
          ))}
          {(data?.rows.length ?? 0) === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground">
                No data.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell>Average winrate</TableCell>
            <TableCell
              colSpan={6}
              className={cn('font-mono', winrateTextClass(data?.average_winrate ?? null))}
            >
              {formatPercent(data?.average_winrate ?? null)}
            </TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    </Card>
  )
}
