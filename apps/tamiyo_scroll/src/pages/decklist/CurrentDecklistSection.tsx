import { useActiveDeck } from '@/contexts/active-deck-context'
import { useDecklistVersions, useDecklistView } from '@/hooks/useDecklistVersions'
import {
  DECKLIST_LINE_STATUS_LABELS,
  DECKLIST_LINE_STATUS_TEXT_CLASS,
  formatDateTime,
} from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'

const LEGEND_STATUSES = ['in_test', 'validated', 'rejected'] as const

export function CurrentDecklistSection() {
  const { activeDeckId } = useActiveDeck()
  const { data: versions } = useDecklistVersions(activeDeckId)
  const { data: lines } = useDecklistView(activeDeckId)

  if (activeDeckId === null) {
    return (
      <Card>
        <CardTitle>Decklist courante</CardTitle>
        <CardDescription className="mt-1">
          Sélectionnez ou créez un deck personnel dans l&apos;en-tête pour afficher sa
          decklist.
        </CardDescription>
      </Card>
    )
  }

  const latest = versions?.[0]

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CardTitle>Decklist courante</CardTitle>
        {latest && (
          <div className="flex items-center gap-2">
            <Badge variant="accent">VERSION {latest.version}</Badge>
            <span className="text-[12.5px] text-muted-foreground">
              {formatDateTime(latest.created_at)}
            </span>
          </div>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-[11.5px] text-muted-foreground">
        {LEGEND_STATUSES.map((status) => (
          <span key={status} className="flex items-center gap-1.5">
            <span
              className={cn(
                'size-2.5 rounded-full',
                DECKLIST_LINE_STATUS_TEXT_CLASS[status].replace('text-', 'bg-'),
              )}
            />
            {DECKLIST_LINE_STATUS_LABELS[status]}
          </span>
        ))}
      </div>

      {!latest && (
        <p className="mt-4 text-muted-foreground">
          Aucune version enregistrée pour ce deck.
        </p>
      )}

      {latest && (
        <div className="mt-4 rounded-(--radius-input) border border-border bg-input-inline p-4 font-mono text-[13px]">
          {lines?.map((line, index) => (
            <p
              key={`${String(index)}-${line.line}`}
              className={DECKLIST_LINE_STATUS_TEXT_CLASS[line.status]}
            >
              {line.line}
            </p>
          ))}
          {(lines?.length ?? 0) === 0 && (
            <p className="text-muted-foreground">Version vide.</p>
          )}
        </div>
      )}
    </Card>
  )
}
