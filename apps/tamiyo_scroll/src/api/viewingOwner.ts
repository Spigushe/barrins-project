import { createStore } from '@/lib/store'

const VIEWING_OWNER_KEY = 'tamiyo_viewing_owner'

/**
 * Utilisateur "vu" en lecture seule (sélecteur "Voir : {utilisateur}" du
 * header) — `null` signifie "mes propres données". Stocké en sessionStorage
 * (par onglet, pas besoin de persister entre sessions).
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
