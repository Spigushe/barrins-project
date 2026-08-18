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
                Share one roster across all your decks of the same game (MtG, YGO,
                PKM, ...)
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
