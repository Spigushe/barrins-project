import { useState } from 'react'
import { AccountScreen } from '@barrins/goblin-guide'
import { useLocalStorageFlag } from '@/hooks/useLocalStorageFlag'
import { useMySettings, useUpdateMySettings } from '@/hooks/useSettings'
import {
  DISPLAY_PREF_MATCHUP_RESULT_FORMAT_2W0L,
  DISPLAY_PREF_MATCHUP_ROW_TINT,
  DISPLAY_PREF_ROSTER_ARCHETYPE_COLOR,
  DISPLAY_PREF_ROSTER_TIER_COLOR,
} from '@/lib/displayPrefs'
import { AccountSettingsTeamSection } from './AccountSettingsTeamSection'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'

/**
 * Account settings popup.
 *
 * Identity-owned account management (display name, email change, account
 * deletion) is the shared Goblin Guide `<AccountScreen>` — it talks to
 * `barrins_identity` directly. Everything below it is Tamiyo-only and hits
 * `barrins_api`: the `data_shared` / `receive_shared_data` sharing toggles
 * (Save/Cancel form state), the four `localStorage`-backed display
 * preferences (applied immediately), and the "Team de test" section
 * (`AccountSettingsTeamSection`, S2 — acts immediately on click).
 *
 * Per docs/project/v2.0.0-bump/z_handoff_params_popup/: the "View:
 * {other user}" selector is deliberately NOT in this popup.
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
  const { data: settings } = useMySettings()
  const updateSettings = useUpdateMySettings()

  const [shareMyData, setShareMyData] = useState(() => settings?.data_shared ?? false)
  const [receiveSharedData, setReceiveSharedData] = useState(
    () => settings?.receive_shared_data ?? false,
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
  const [rosterArchetypeColorEnabled, setRosterArchetypeColorEnabled] = useLocalStorageFlag(
    DISPLAY_PREF_ROSTER_ARCHETYPE_COLOR,
    false,
  )
  const [rosterTierColorEnabled, setRosterTierColorEnabled] = useLocalStorageFlag(
    DISPLAY_PREF_ROSTER_TIER_COLOR,
    false,
  )

  const saving = updateSettings.isPending

  async function handleSave() {
    await updateSettings.mutateAsync({
      data_shared: shareMyData,
      receive_shared_data: receiveSharedData,
    })
    onClose()
  }

  return (
    <DialogContent className="max-w-[480px]">
      <DialogTitle>Account settings</DialogTitle>
      <div className="flex flex-col gap-[22px]">
        <AccountScreen
          title="Barrin's account"
          subtitle="Your sign-in across every app in the ecosystem."
        />

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
          <p className="text-[13.5px] font-semibold text-foreground">Display</p>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">Winrate row tint</p>
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

        <div role="separator" className="h-px bg-accent" />

        <AccountSettingsTeamSection onClose={onClose} />

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
