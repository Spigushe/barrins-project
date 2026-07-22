import { createStore } from '@/lib/store'

const VIEWING_OWNER_KEY = 'tamiyo_viewing_owner'

/**
 * User being "viewed" in read-only mode (the "View: {user}" selector in the
 * header) — `null` means "my own data". Stored in sessionStorage (per tab,
 * no need to persist across sessions).
 */
export interface ViewingOwner {
  id: string
  label: string
}

function loadViewingOwner(): ViewingOwner | null {
  const raw = sessionStorage.getItem(VIEWING_OWNER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as ViewingOwner
  } catch {
    return null
  }
}

export const viewingOwnerStore = createStore<ViewingOwner | null>(loadViewingOwner())

export function setViewingOwner(owner: ViewingOwner | null): void {
  if (owner) {
    sessionStorage.setItem(VIEWING_OWNER_KEY, JSON.stringify(owner))
  } else {
    sessionStorage.removeItem(VIEWING_OWNER_KEY)
  }
  viewingOwnerStore.set(owner)
}
