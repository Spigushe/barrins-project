import { useSyncExternalStore } from 'react'
import { type ViewingOwner, viewingOwnerStore } from '@/api/viewingOwner'

/** User currently being "viewed" in read-only mode, or `null` for one's own data. */
export function useViewingOwner(): ViewingOwner | null {
  return useSyncExternalStore(
    viewingOwnerStore.subscribe,
    viewingOwnerStore.get,
    viewingOwnerStore.get,
  )
}
