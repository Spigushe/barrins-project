import { useActiveDeck } from '@/contexts/active-deck-context'
import { useDecklistVersions, useDecklistView } from '@/hooks/useDecklistVersions'
import { useDownloadDeckReport, usePersonalDecks } from '@/hooks/usePersonalDecks'
import {
  DECKLIST_CARD_CATEGORY_LABELS,
  DECKLIST_LINE_STATUS_BG_CLASS,
  DECKLIST_LINE_STATUS_LABELS,
  DECKLIST_LINE_STATUS_TEXT_CLASS,
  deckReportFilename,
  formatDateTime,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableHeader, TableRow, TableHead } from '@/components/ui/table'
import { DecklistCardRow } from './DecklistCardRow'

const LEGEND_STATUSES = ['in_test', 'validated', 'rejected'] as const

export function CurrentDecklistSection() {
  const { activeDeckId } = useActiveDeck()
  const { data: versions } = useDecklistVersions(activeDeckId)
  const { data: view } = useDecklistView(activeDeckId)
  const { data: personalDecks } = usePersonalDecks()
  const downloadReport = useDownloadDeckReport()

  if (activeDeckId === null) return null

  const latest = versions?.[0]
  const activeDeck = personalDecks?.find((deck) => deck.id === activeDeckId)

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CardTitle>Current decklist</CardTitle>
        <div className="ml-auto flex items-center gap-2">
          {latest && (
            <>
              <Badge variant="accent">VERSION {latest.version}</Badge>
              <span className="text-[12.5px] text-muted-foreground">
                {formatDateTime(latest.created_at)}
              </span>
            </>
          )}
          <div className="flex flex-wrap items-center gap-3 text-[11.5px] text-muted-foreground">
            {LEGEND_STATUSES.map((status) => (
              <span key={status} className="flex items-center gap-1.5">
                <span
                  className={cn(
                    'size-2.5 rounded-full',
                    DECKLIST_LINE_STATUS_BG_CLASS[status],
                  )}
                />
                {DECKLIST_LINE_STATUS_LABELS[status]}
              </span>
            ))}
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={downloadReport.isPending || !activeDeck}
            onClick={() => {
              if (!activeDeck) return
              downloadReport.mutate({
                deckId: activeDeck.id,
                filename: deckReportFilename(activeDeck),
              })
            }}
          >
            {downloadReport.isPending ? 'Generating…' : 'Download report (PDF)'}
          </Button>
        </div>
      </div>

      {!latest && (
        <p className="mt-4 text-muted-foreground">No version saved for this deck.</p>
      )}

      {latest && (
        <div className="mt-4 rounded-(--radius-input) border border-border bg-input-inline p-4">
          {view && view.commander_cards.length > 0 && (
            <div className="mb-4">
              <p className="text-[11.5px] font-semibold uppercase tracking-[0.04em] text-muted-foreground">
                Commander ({view.commander_cards.length})
              </p>
              <Table className="table-fixed">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Qty</TableHead>
                    <TableHead className="w-64">Name</TableHead>
                    <TableHead className="w-16">Color pips</TableHead>
                    <TableHead className="w-16">Popover</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {view.commander_cards.map((card) => (
                    <DecklistCardRow key={card.name} card={card} />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {view &&
            view.library_cards.map((group) => (
              <div key={group.category} className="mb-4 last:mb-0">
                <p className="text-[11.5px] font-semibold uppercase tracking-[0.04em] text-muted-foreground">
                  {DECKLIST_CARD_CATEGORY_LABELS[group.category]} ({group.count})
                </p>
                <Table className="table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">Qty</TableHead>
                      <TableHead className="w-64">Name</TableHead>
                      <TableHead className="w-16">Color pips</TableHead>
                      <TableHead className="w-16">Popover</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {group.cards.map((card) => (
                      <DecklistCardRow key={card.name} card={card} />
                    ))}
                  </TableBody>
                </Table>
              </div>
            ))}

          {view && view.unparsed_lines.length > 0 && (
            <div className="mt-4 font-mono text-[13px]">
              {view.unparsed_lines.map((line, index) => (
                <p
                  key={`${String(index)}-${line.line}`}
                  className={DECKLIST_LINE_STATUS_TEXT_CLASS[line.status]}
                >
                  {line.line}
                </p>
              ))}
            </div>
          )}

          {view &&
            view.commander_cards.length === 0 &&
            view.library_cards.length === 0 &&
            view.unparsed_lines.length === 0 && (
              <p className="text-muted-foreground">Empty version.</p>
            )}
        </div>
      )}
    </Card>
  )
}
