import { createContext, useContext } from 'react'
import type { IdentityClient } from './client'
import type { TokenStore } from './tokenStore'

export interface IdentityContextValue {
  client: IdentityClient
  tokenStore: TokenStore
  /**
   * Cookie mode only (ADR-18): `true` while the provider is making its
   * one-shot `POST /auth/refresh` attempt to restore a session from the
   * `HttpOnly` cookie on page load. Always `false` in body mode. Consumers
   * should hold off on the "signed in vs. login screen" decision until this
   * clears — see {@link useIdentity}.
   */
  isBootstrapping: boolean
}

export const IdentityContext = createContext<IdentityContextValue | null>(null)

export function useIdentityContext(): IdentityContextValue {
  const value = useContext(IdentityContext)
  if (value === null) {
    throw new Error('Goblin Guide hooks must be used within <IdentityProvider>.')
  }
  return value
}
