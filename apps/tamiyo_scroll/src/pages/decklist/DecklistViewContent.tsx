import {
  DECKLIST_CARD_CATEGORY_LABELS,
  DECKLIST_LINE_STATUS_TEXT_CLASS,
} from '@/lib/mtg-format'
import { Table, TableBody, TableHeader, TableRow, TableHead } from '@/components/ui/table'
import type { DecklistView } from '@/schemas/tamiyoScroll'
import { DecklistCardRow } from './DecklistCardRow'

/**
 * Structured Commander/Library rendering of a `DecklistView` — shared by
 * `CurrentDecklistSection` (latest version) and `VersionHistorySection`'s
 * expand-in-place past-version view (S15), so the two never drift.
 */
export function DecklistViewContent({ view }: { view: DecklistView }) {
  const isEmpty =
    view.commander_cards.length === 0 &&
    view.library_cards.length === 0 &&
    view.unparsed_lines.length === 0

  if (isEmpty) {
    return <p className="text-muted-foreground">Empty version.</p>
  }

  return (
    <>
      {view.commander_cards.length > 0 && (
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

      {view.library_cards.map((group) => (
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

      {view.unparsed_lines.length > 0 && (
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
    </>
  )
}
