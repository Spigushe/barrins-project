import { useSyncExternalStore } from 'react'
import { type ViewingOwner, viewingOwnerStore } from '@/api/viewingOwner'

/** Utilisateur actuellement "vu" en lecture seule, ou `null` pour ses propres données. */
export function useViewingOwner(): ViewingOwner | null {
  return useSyncExternalStore(
    viewingOwnerStore.subscribe,
    viewingOwnerStore.get,
    viewingOwnerStore.get,
  )
}
