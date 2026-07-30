import { useCurrentUser } from '@/hooks/useAuth'
import {
  useAvailableSharers,
  useCreateReceiveOptIn,
  useDeleteReceiveOptIn,
  useMySettings,
  useSharedUsers,
  useUpdateMySettings,
} from '@/hooks/useSettings'
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

/** "Share my data" toggle, per-sharer "receive" opt-ins, and "View: {user}" selector. */
export function SharingControls() {
  return <SharingControlsContent />
}

export function SharingControlsContent() {
  const { data: currentUser } = useCurrentUser()
  const { data: settings } = useMySettings()
  const { data: sharedUsers } = useSharedUsers()
  const { data: availableSharers } = useAvailableSharers()
  const viewingOwner = useViewingOwner()
  const updateSettings = useUpdateMySettings()
  const createReceiveOptIn = useCreateReceiveOptIn()
  const deleteReceiveOptIn = useDeleteReceiveOptIn()

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

  function handleReceiveToggle(sharerId: string, checked: boolean) {
    if (checked) {
      void createReceiveOptIn.mutateAsync(sharerId)
    } else {
      void deleteReceiveOptIn.mutateAsync(sharerId)
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

      {availableSharers && availableSharers.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-[13px] text-muted-foreground">
            Receive shared data from:
          </span>
          {availableSharers.map((sharer) => (
            <label
              key={sharer.id}
              className="flex items-center gap-2 text-[13px] text-foreground"
            >
              <Checkbox
                checked={sharer.opted_in}
                onCheckedChange={(checked) => {
                  handleReceiveToggle(sharer.id, checked === true)
                }}
              />
              {sharer.display_name ?? sharer.email}
            </label>
          ))}
        </div>
      )}
    </>
  )
}
