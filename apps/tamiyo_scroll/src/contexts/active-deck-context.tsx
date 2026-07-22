import { createContext, useContext } from 'react'

export interface ActiveDeckContextValue {
  activeDeckId: string | null
  canEdit: boolean
}

export const ActiveDeckContext = createContext<ActiveDeckContextValue | null>(null)

/** Deck personnel actuellement sélectionné dans le header, et si l'édition est permise. */
export function useActiveDeck(): ActiveDeckContextValue {
  const value = useContext(ActiveDeckContext)
  if (!value) {
    throw new Error('useActiveDeck must be used within AppShell')
  }
  return value
}
