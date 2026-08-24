import { useState } from 'react'
import { useActiveDeck } from '@/contexts/active-deck-context'
import {
  useDecklistVersionDiff,
  useDecklistVersions,
  useDecklistVersionView,
  useDeleteDecklistVersion,
} from '@/hooks/useDecklistVersions'
import { useMySettings } from '@/hooks/useSettings'
import type { DecklistVersion, DecklistVersionDiff } from '@/schemas/tamiyoScroll'
import {
  DECKLIST_CARD_DIFF_STATUS_TEXT_CLASS,
  DECKLIST_VERSION_SOURCE_LABELS,
  formatDateTime,
} from '@/lib/mtg-format'
import { Button } from '@/components/ui/button'
import { Card, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { DecklistViewContent } from './DecklistViewContent'

export function VersionHistorySection() {
  const { activeDeckId, canEdit } = useActiveDeck()
  const { data: versions } = useDecklistVersions(activeDeckId)
  const deleteVersion = useDeleteDecklistVersion()
  const [pendingDelete, setPendingDelete] = useState<DecklistVersion | null>(null)
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null)

  if (activeDeckId === null) return null
  const deckId = activeDeckId

  return (
    <Card>
      <CardTitle>Version history</CardTitle>
      <div className="mt-3 flex flex-col gap-2">
        {versions?.map((version) => (
          <div key={version.id} className="flex flex-col gap-2">
            <div
              role="button"
              tabIndex={0}
              className="flex cursor-pointer items-center justify-between gap-3 rounded-(--radius-input) border border-border bg-input-inline px-3 py-2"
              onClick={() => {
                setExpandedVersionId((current) =>
                  current === version.id ? null : version.id,
                )
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setExpandedVersionId((current) =>
                    current === version.id ? null : version.id,
                  )
                }
              }}
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
                  onClick={(event) => {
                    event.stopPropagation()
                    setPendingDelete(version)
                  }}
                >
                  ✕
                </Button>
              )}
            </div>

            {expandedVersionId === version.id && (
              <ExpandedVersion deckId={deckId} versionId={version.id} />
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

/** S15: a version's full content, expanded in place; the diff against the
 * immediately-prior version is added below it when the opt-in setting is on. */
function ExpandedVersion({ deckId, versionId }: { deckId: string; versionId: string }) {
  const { data: settings } = useMySettings()
  const showDiff = settings?.show_decklist_version_diff ?? true
  const { data: view } = useDecklistVersionView(deckId, versionId, !showDiff)
  const { data: diff } = useDecklistVersionDiff(deckId, versionId, showDiff)

  return (
    <div className="rounded-(--radius-input) border border-border bg-input-inline p-4">
      {showDiff
        ? diff && <VersionDiff diff={diff} />
        : view && <DecklistViewContent view={view} />}
    </div>
  )
}

function VersionDiff({ diff }: { diff: DecklistVersionDiff }) {
  const { data: settings } = useMySettings()
  const showChangeLog = settings?.show_decklist_change_log ?? false

  if (diff.compared_to_version === null) {
    return (
      <p className="text-muted-foreground">
        This is the first version — no prior version to compare against.
      </p>
    )
  }

  const changedCards = diff.cards.filter((card) => card.status !== 'unchanged')
  const changedLines = diff.unparsed_lines.filter((line) => line.status !== 'unchanged')

  return (
    <div className="flex flex-col gap-1">
      <p className="text-[11.5px] font-semibold uppercase tracking-[0.04em] text-muted-foreground">
        Diff vs version {diff.compared_to_version}
      </p>
      {changedCards.length === 0 && changedLines.length === 0 && (
        <p className="text-muted-foreground">No changes.</p>
      )}
      <div className="font-mono text-[13px]">
        {changedCards.map((card) => (
          <div key={card.name}>
            <p className={DECKLIST_CARD_DIFF_STATUS_TEXT_CLASS[card.status]}>
              {card.status === 'added' && `+ ${String(card.new_qty)} ${card.name}`}
              {card.status === 'removed' && `- ${String(card.old_qty)} ${card.name}`}
              {card.status === 'quantity_changed' &&
                `${card.name}: ${String(card.old_qty)} → ${String(card.new_qty)}`}
            </p>
            {showChangeLog &&
              card.card_test_notes.map((note, index) => (
                <p
                  key={`${card.name}-note-${String(index)}`}
                  className="pl-4 font-sans text-[12px] text-muted-foreground italic"
                >
                  {note}
                </p>
              ))}
          </div>
        ))}
        {changedLines.map((line, index) => (
          <p
            key={`${String(index)}-${line.line}`}
            className={line.status === 'added' ? 'text-success' : 'text-destructive'}
          >
            {line.status === 'added' ? `+ ${line.line}` : `- ${line.line}`}
          </p>
        ))}
      </div>
    </div>
  )
}
