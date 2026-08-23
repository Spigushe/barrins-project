import { useState } from 'react'
import { useActiveDeck } from '@/contexts/active-deck-context'
import {
  useDecklistVersions,
  useDeleteDecklistVersion,
} from '@/hooks/useDecklistVersions'
import type { DecklistVersion } from '@/schemas/tamiyoScroll'
import { DECKLIST_VERSION_SOURCE_LABELS, formatDateTime } from '@/lib/mtg-format'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'

export function VersionHistorySection() {
  const { activeDeckId, canEdit } = useActiveDeck()
  const { data: versions } = useDecklistVersions(activeDeckId)
  const deleteVersion = useDeleteDecklistVersion()
  const [pendingDelete, setPendingDelete] = useState<DecklistVersion | null>(null)

  if (activeDeckId === null) return null
  const deckId = activeDeckId

  return (
    <Card>
      <CardTitle>Version history</CardTitle>
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
                  setPendingDelete(version)
                }}
              >
                ✕
              </Button>
            )}
          </div>
        ))}
        {(versions?.length ?? 0) === 0 && (
          <p className="text-center text-muted-foreground">No version saved.</p>
        )}
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(next) => {
          if (!next) setPendingDelete(null)
        }}
        title={pendingDelete ? `Delete version ${pendingDelete.version}?` : ''}
        description="It will disappear from this deck's version history. This can't be undone."
        confirmDisabled={deleteVersion.isPending}
        onConfirm={() => {
          if (!pendingDelete) return
          void deleteVersion.mutateAsync({ deckId, versionId: pendingDelete.id })
          setPendingDelete(null)
        }}
      />
    </Card>
  )
}
