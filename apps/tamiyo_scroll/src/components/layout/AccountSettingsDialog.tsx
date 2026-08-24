import { useState } from 'react'
import { useCurrentUser, useUpdateProfile } from '@/hooks/useAuth'
import { useLocalStorageFlag } from '@/hooks/useLocalStorageFlag'
import { useMySettings, useUpdateMySettings } from '@/hooks/useSettings'
import type { MetagameRosterScope } from '@/schemas/tamiyoScroll'
import {
  DISPLAY_PREF_MATCHUP_RESULT_FORMAT_2W0L,
  DISPLAY_PREF_MATCHUP_ROW_TINT,
  DISPLAY_PREF_ROSTER_ARCHETYPE_COLOR,
  DISPLAY_PREF_ROSTER_TIER_COLOR,
} from '@/lib/displayPrefs'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

/**
 * Account settings popup — replaces the header's old inline "Share my
 * data" checkbox with a modal (display name + share/receive toggles).
 *
 * Per docs/project/v2.0.0-bump/z_handoff_params_popup/: the "View:
 * {other user}" selector is deliberately NOT in this popup — its UI
 * entry point was removed from the header entirely (not this popup's
 * scope; where/whether it resurfaces is a product decision). The
 * underlying read-as-another-user mechanism (`useViewingOwner`,
 * `applyOwnerParam`) is untouched.
 */
export function AccountSettingsDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* Mounted only while open, so its form state initializes once from
          the lazy useState below — never clobbered by a parent re-render
          with a same-value-but-new-reference query result mid-edit. */}
      {open && <AccountSettingsForm onClose={() => onOpenChange(false)} />}
    </Dialog>
  )
}

function AccountSettingsForm({ onClose }: { onClose: () => void }) {
  const { data: currentUser } = useCurrentUser()
  const { data: settings } = useMySettings()
  const updateProfile = useUpdateProfile()
  const updateSettings = useUpdateMySettings()

  const [displayName, setDisplayName] = useState(() => currentUser?.display_name ?? '')
  const [shareMyData, setShareMyData] = useState(() => settings?.data_shared ?? false)
  const [receiveSharedData, setReceiveSharedData] = useState(
    () => settings?.receive_shared_data ?? false,
  )
  // Server-persisted (F10), unlike the S12 toggles below — it changes what
  // GET /meta-decks returns, not just how the frontend renders it.
  const [rosterScope, setRosterScope] = useState<MetagameRosterScope>(
    () => settings?.metagame_roster_scope ?? 'game',
  )
  // S14 item 9: opted-in by default, server-persisted — the periodic-job
  // question the doc raised is moot here since the sweep runs on decklist
  // import, not on a schedule.
  const [autoArchiveEnabled, setAutoArchiveEnabled] = useState(
    () => settings?.auto_archive_stale_sessions ?? true,
  )
  // Kept as raw text (not a number) so the field can be freely cleared
  // and retyped — clamping happens once, on save.
  const [autoArchiveGapText, setAutoArchiveGapText] = useState(() =>
    String(settings?.auto_archive_decklist_version_gap ?? 2),
  )
  // S15: defaults on (2026-08-24), server-persisted — when on, expanding a
  // version in VersionHistorySection shows its diff against the prior
  // version instead of its full content.
  const [showVersionDiff, setShowVersionDiff] = useState(
    () => settings?.show_decklist_version_diff ?? true,
  )
  // S16: write-time validations for card tests. Removed-card defaults on
  // (matches show_decklist_version_diff's opt-out convention); added-card
  // stays opt-in since an unresolvable-but-legitimate name is a more
  // likely false positive.
  const [validateRemovedCardInDecklist, setValidateRemovedCardInDecklist] = useState(
    () => settings?.validate_removed_card_in_decklist ?? true,
  )
  const [validateAddedCardExists, setValidateAddedCardExists] = useState(
    () => settings?.validate_added_card_exists ?? false,
  )
  // S16: gates both the matched-card-test comments on decklist diffs and
  // the standalone unmatched-entries list on the current decklist.
  const [showChangeLog, setShowChangeLog] = useState(
    () => settings?.show_decklist_change_log ?? false,
  )

  // S12 items 8-11: four purely-visual toggles, `localStorage`-backed
  // (not part of the Save/Cancel form above — they apply immediately,
  // same as the game/category migration notice's dismiss button in
  // `PersonalDeckSelector.tsx`).
  const [rowTintEnabled, setRowTintEnabled] = useLocalStorageFlag(
    DISPLAY_PREF_MATCHUP_ROW_TINT,
    true,
  )
  const [resultFormat2w0lEnabled, setResultFormat2w0lEnabled] = useLocalStorageFlag(
    DISPLAY_PREF_MATCHUP_RESULT_FORMAT_2W0L,
    false,
  )
  const [rosterArchetypeColorEnabled, setRosterArchetypeColorEnabled] =
    useLocalStorageFlag(DISPLAY_PREF_ROSTER_ARCHETYPE_COLOR, false)
  const [rosterTierColorEnabled, setRosterTierColorEnabled] = useLocalStorageFlag(
    DISPLAY_PREF_ROSTER_TIER_COLOR,
    false,
  )

  const saving = updateProfile.isPending || updateSettings.isPending

  async function handleSave() {
    await Promise.all([
      updateProfile.mutateAsync({ display_name: displayName.trim() || null }),
      updateSettings.mutateAsync({
        data_shared: shareMyData,
        receive_shared_data: receiveSharedData,
        metagame_roster_scope: rosterScope,
        auto_archive_stale_sessions: autoArchiveEnabled,
        auto_archive_decklist_version_gap: Math.max(
          1,
          Number.parseInt(autoArchiveGapText, 10) || 1,
        ),
        show_decklist_version_diff: showVersionDiff,
        validate_removed_card_in_decklist: validateRemovedCardInDecklist,
        validate_added_card_exists: validateAddedCardExists,
        show_decklist_change_log: showChangeLog,
      }),
    ])
    onClose()
  }

  return (
    <DialogContent className="max-w-[440px]">
      <DialogTitle>Account settings</DialogTitle>
      <div className="flex flex-col gap-[22px]">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="account-display-name">Display name</Label>
          <Input
            id="account-display-name"
            value={displayName}
            placeholder={currentUser?.email ?? ''}
            onChange={(event) => {
              setDisplayName(event.target.value)
            }}
          />
          <p className="text-xs text-muted-foreground">
            Shown instead of your email throughout the interface.
          </p>
        </div>

        <div role="separator" className="h-px bg-accent" />

        <div className="flex flex-col gap-3.5 rounded-[10px] bg-input-inline p-3.5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">Share my data</p>
              <p className="text-xs text-muted-foreground">
                Your decks, matches and card tests become visible to other accounts.
              </p>
            </div>
            <Switch
              checked={shareMyData}
              onCheckedChange={(checked) => {
                setShareMyData(checked)
                // Receiving requires sharing on the same account — clear it
                // rather than leave an unreachable-but-saved combination.
                if (!checked) {
                  setReceiveSharedData(false)
                }
              }}
              label="Share my data"
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Receive shared data
              </p>
              <p className="text-xs text-muted-foreground">
                See data shared by other accounts that enabled sharing.
              </p>
            </div>
            <Switch
              checked={receiveSharedData}
              onCheckedChange={setReceiveSharedData}
              label="Receive shared data"
              disabled={!shareMyData}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Sharing is matched by deck name: a shared match or roster entry only merges
            into a deck of yours with the exact same name.
          </p>
        </div>

        <div role="separator" className="h-px bg-accent" />

        <div className="flex flex-col gap-3.5 rounded-[10px] bg-input-inline p-3.5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Store roster decks per game
              </p>
              <p className="text-xs text-muted-foreground">
                Share one roster across all your decks of the same game (MtG, YGO, PKM,
                ...)
              </p>
            </div>
            <Switch
              checked={rosterScope === 'game'}
              onCheckedChange={(checked) => {
                setRosterScope(checked ? 'game' : 'personal_deck')
              }}
              label="Store roster decks per game"
            />
          </div>
        </div>

        <div role="separator" className="h-px bg-accent" />

        <div className="flex flex-col gap-3.5 rounded-[10px] bg-input-inline p-3.5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Auto-archive stale sessions
              </p>
              <p className="text-xs text-muted-foreground">
                Archive a session automatically once its last logged match falls this many
                decklist versions behind, on your next decklist import.
              </p>
            </div>
            <Switch
              checked={autoArchiveEnabled}
              onCheckedChange={setAutoArchiveEnabled}
              label="Auto-archive stale sessions"
            />
          </div>
          {autoArchiveEnabled && (
            <div className="flex items-center gap-2">
              <Label htmlFor="auto-archive-gap" className="text-xs text-muted-foreground">
                Version gap
              </Label>
              <Input
                id="auto-archive-gap"
                type="number"
                min={1}
                value={autoArchiveGapText}
                onChange={(event) => {
                  setAutoArchiveGapText(event.target.value)
                }}
                className="w-20"
              />
            </div>
          )}
        </div>

        <div role="separator" className="h-px bg-accent" />

        <div className="flex flex-col gap-3.5 rounded-[10px] bg-input-inline p-3.5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Decklist version diff
              </p>
              <p className="text-xs text-muted-foreground">
                Show a diff against the prior version when you expand a version in the
                deck's version history.
              </p>
            </div>
            <Switch
              checked={showVersionDiff}
              onCheckedChange={setShowVersionDiff}
              label="Decklist version diff"
            />
          </div>
        </div>

        <div role="separator" className="h-px bg-accent" />

        <div className="flex flex-col gap-3.5 rounded-[10px] bg-input-inline p-3.5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Validate removed card is in decklist
              </p>
              <p className="text-xs text-muted-foreground">
                Reject a card test's Removed Card unless it's present in the deck's
                current decklist.
              </p>
            </div>
            <Switch
              checked={validateRemovedCardInDecklist}
              onCheckedChange={setValidateRemovedCardInDecklist}
              label="Validate removed card is in decklist"
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Validate added card exists
              </p>
              <p className="text-xs text-muted-foreground">
                Reject a card test's Added Card unless it resolves to a known card. Magic:
                The Gathering only — non-Magic decks should leave this off.
              </p>
            </div>
            <Switch
              checked={validateAddedCardExists}
              onCheckedChange={setValidateAddedCardExists}
              label="Validate added card exists"
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Show decklist change log
              </p>
              <p className="text-xs text-muted-foreground">
                Show a card test's note as a comment on the decklist diff it matches, and
                list unmatched card tests on the current decklist.
              </p>
            </div>
            <Switch
              checked={showChangeLog}
              onCheckedChange={setShowChangeLog}
              label="Show decklist change log"
            />
          </div>
        </div>

        <div role="separator" className="h-px bg-accent" />

        <div className="flex flex-col gap-3.5 rounded-[10px] bg-input-inline p-3.5">
          <p className="text-[13.5px] font-semibold text-foreground">Display</p>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Winrate row tint
              </p>
              <p className="text-xs text-muted-foreground">
                Color match-up summary rows red/green for very negative/positive winrates.
              </p>
            </div>
            <Switch
              checked={rowTintEnabled}
              onCheckedChange={setRowTintEnabled}
              label="Winrate row tint"
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                "2W / 0L" result format
              </p>
              <p className="text-xs text-muted-foreground">
                Show W/L OTP and W/L OTD as "2W / 0L" instead of "2-0".
              </p>
            </div>
            <Switch
              checked={resultFormat2w0lEnabled}
              onCheckedChange={setResultFormat2w0lEnabled}
              label='"2W / 0L" result format'
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Colored archetype cell
              </p>
              <p className="text-xs text-muted-foreground">
                Color the deck roster's archetype cell, matching "Breakdown by archetype".
              </p>
            </div>
            <Switch
              checked={rosterArchetypeColorEnabled}
              onCheckedChange={setRosterArchetypeColorEnabled}
              label="Colored archetype cell"
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">
                Tier background color
              </p>
              <p className="text-xs text-muted-foreground">
                Color the deck roster's Tier cell by a 3-way strong/mid/weak grouping.
              </p>
            </div>
            <Switch
              checked={rosterTierColorEnabled}
              onCheckedChange={setRosterTierColorEnabled}
              label="Tier background color"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2.5">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={saving}
            onClick={() => {
              void handleSave()
            }}
          >
            Save
          </Button>
        </div>
      </div>
    </DialogContent>
  )
}
