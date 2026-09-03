import { useActiveDeck } from '@/contexts/active-deck-context'
import { useCardTestChangeLog } from '@/hooks/useCardTests'
import { useDecklistVersions, useDecklistView } from '@/hooks/useDecklistVersions'
import { useDownloadDeckReport, usePersonalDecks } from '@/hooks/usePersonalDecks'
import { useMySettings } from '@/hooks/useSettings'
import {
  DECKLIST_LINE_STATUS_BG_CLASS,
  DECKLIST_LINE_STATUS_LABELS,
  deckReportFilename,
  formatDateTime,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import type { DecklistView } from '@/schemas/tamiyoScroll'
import { DecklistViewContent } from './DecklistViewContent'

const LEGEND_STATUSES = ['in_test', 'validated', 'rejected'] as const

/** Card-log ids already shown inline as a pending decklist line (S17) —
 * the standalone change-log block below only needs to list what's
 * *not* covered by that inline treatment. */
function pendingCardTestIds(view: DecklistView | undefined): Set<string> {
  const ids = new Set<string>()
  if (!view) return ids
  const allCards = [
    ...view.commander_cards,
    ...view.library_cards.flatMap((group) => group.cards),
  ]
  for (const card of allCards) {
    if (card.pending_card_test_id) ids.add(card.pending_card_test_id)
  }
  return ids
}

export function CurrentDecklistSection() {
  const { activeDeckId } = useActiveDeck()
  const { data: versions } = useDecklistVersions(activeDeckId)
  const { data: view } = useDecklistView(activeDeckId)
  const { data: personalDecks } = usePersonalDecks()
  const { data: settings } = useMySettings()
  const showChangeLog = settings?.show_decklist_change_log ?? false
  const { data: unmatchedCardTests } = useCardTestChangeLog(activeDeckId, showChangeLog)
  const downloadReport = useDownloadDeckReport()

  if (activeDeckId === null) return null

  const inlinePendingIds = pendingCardTestIds(view)
  const standaloneChangeLog = unmatchedCardTests?.filter(
    (test) => !inlinePendingIds.has(test.id),
  )

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

      {showChangeLog && !((standaloneChangeLog?.length ?? 0) === 0) && (
        <div className="mt-4 rounded-(--radius-input) border border-border bg-input-inline p-4">
          <p className="text-[11.5px] font-semibold uppercase tracking-[0.04em] text-muted-foreground">
            Card change being considered in this version:
          </p>
          <div className="mt-1 flex flex-col gap-1.5 font-mono text-[13px]">
            {standaloneChangeLog?.map((test) => (
              <div key={test.id}>
                <p className="font-sans text-muted-foreground">{test.notes ?? '—'}</p>
                <p className="text-destructive">- {test.removed_card_name}</p>
                <p className="text-success">+ {test.added_card_name}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {!latest && (
        <p className="mt-4 text-muted-foreground">No version saved for this deck.</p>
      )}

      {latest && (
        <div className="mt-4 rounded-(--radius-input) border border-border bg-input-inline p-4">
          {view && <DecklistViewContent view={view} />}
        </div>
      )}
    </Card>
  )
}
