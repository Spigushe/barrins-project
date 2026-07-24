import { useCurrentUser } from '@/hooks/useAuth'
import { useMySettings, useSharedUsers, useUpdateMySettings } from '@/hooks/useSettings'
import { useViewingOwner } from '@/hooks/useViewingOwner'
import { setViewingOwner } from '@/api/viewingOwner'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const SELF_VALUE = '__self__'

/**
 * Not mature enough to ship in v1.0.0: the underlying data_shared/owner_id
 * enforcement is fully tested on the backend, but this UI has no
 * component-level test and is disabled until it gets one.
 */
const SHARING_ENABLED = false

/** "Share my data" toggle + "View: {user}" selector for read-only cross-user viewing. */
export function SharingControls() {
  if (!SHARING_ENABLED) return null
  return <SharingControlsContent />
}

/**
 * The actual sharing UI, split out from the `SHARING_ENABLED` gate above so
 * it stays covered by a real render test while disabled, instead of
 * bit-rotting silently.
 */
export function SharingControlsContent() {
  const { data: currentUser } = useCurrentUser()
  const { data: settings } = useMySettings()
  const { data: sharedUsers } = useSharedUsers()
  const viewingOwner = useViewingOwner()
  const updateSettings = useUpdateMySettings()

  function handleViewingChange(value: string) {
    if (value === SELF_VALUE) {
      setViewingOwner(null)
      return
    }
    const user = sharedUsers?.find((candidate) => candidate.id === value)
    if (user) {
      setViewingOwner({ id: user.id, label: user.display_name ?? user.email })
    }
  }

  return (
    <>
      {viewingOwner !== null && (
        <Badge variant="warning">Viewing: {viewingOwner.label} · read only</Badge>
      )}

      <Select value={viewingOwner?.id ?? SELF_VALUE} onValueChange={handleViewingChange}>
        <SelectTrigger className="w-56">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={SELF_VALUE}>
            My account ({currentUser?.email ?? '…'})
          </SelectItem>
          {sharedUsers?.map((user) => (
            <SelectItem key={user.id} value={user.id}>
              View: {user.display_name ?? user.email}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <label className="flex items-center gap-2 text-[13px] text-foreground">
        <Checkbox
          checked={settings?.data_shared ?? false}
          onCheckedChange={(checked) => {
            void updateSettings.mutateAsync({ data_shared: checked === true })
          }}
        />
        Share my data
      </label>
    </>
  )
}
