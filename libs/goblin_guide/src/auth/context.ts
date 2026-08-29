import { createContext, useContext } from 'react'
import type { IdentityClient } from './client'
import type { TokenStore } from './tokenStore'

export interface IdentityContextValue {
  client: IdentityClient
  tokenStore: TokenStore
}

export const IdentityContext = createContext<IdentityContextValue | null>(null)

export function useIdentityContext(): IdentityContextValue {
  const value = useContext(IdentityContext)
  if (value === null) {
    throw new Error('Goblin Guide hooks must be used within <IdentityProvider>.')
  }
  return value
}
