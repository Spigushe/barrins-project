import { useActiveDeck } from '@/contexts/active-deck-context'
import {
  useDecklistVersions,
  useDeleteDecklistVersion,
} from '@/hooks/useDecklistVersions'
import { DECKLIST_VERSION_SOURCE_LABELS, formatDateTime } from '@/lib/mtg-format'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'

export function VersionHistorySection() {
  const { activeDeckId, canEdit } = useActiveDeck()
  const { data: versions } = useDecklistVersions(activeDeckId)
  const deleteVersion = useDeleteDecklistVersion()

  if (activeDeckId === null) return null
  const deckId = activeDeckId

  return (
    <Card>
      <CardTitle>Historique des versions</CardTitle>
      <div className="mt-3 flex flex-col gap-2">
        {versions?.map((version) => (
          <div
            key={version.id}
            className="flex items-center justify-between gap-3 rounded-(--radius-input) border border-border bg-input-inline px-3 py-2"
          >
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-semibold text-foreground">
                Version {version.version}
              </span>
              <span className="text-[12.5px] text-muted-foreground">
                {formatDateTime(version.created_at)}
              </span>
              <span className="text-[12.5px] text-subtle-foreground">
                {DECKLIST_VERSION_SOURCE_LABELS[version.source]}
              </span>
            </div>
            {canEdit && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => {
                  void deleteVersion.mutateAsync({ deckId, versionId: version.id })
                }}
              >
                ✕
              </Button>
            )}
          </div>
        ))}
        {(versions?.length ?? 0) === 0 && (
          <p className="text-center text-muted-foreground">Aucune version enregistrée.</p>
        )}
      </div>
    </Card>
  )
}
