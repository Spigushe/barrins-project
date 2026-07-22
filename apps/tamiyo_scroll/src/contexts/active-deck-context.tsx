import { createContext, useContext } from 'react'

export interface ActiveDeckContextValue {
  activeDeckId: string | null
  canEdit: boolean
}

export const ActiveDeckContext = createContext<ActiveDeckContextValue | null>(null)

/** Currently selected personal deck in the header, and whether editing is allowed. */
export function useActiveDeck(): ActiveDeckContextValue {
  const value = useContext(ActiveDeckContext)
  if (!value) {
    throw new Error('useActiveDeck must be used within AppShell')
  }
  return value
}
