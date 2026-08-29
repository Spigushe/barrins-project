import { type ReactNode, useMemo } from 'react'
import { createIdentityClient, type FetchLike } from './client'
import { IdentityContext, type IdentityContextValue } from './context'
import { createMemoryTokenStore, type TokenStore } from './tokenStore'

export interface IdentityConfig {
  /** Base URL of the Barrin's Identity service. */
  serviceUrl: string
  /**
   * Token storage strategy. Defaults to an in-memory store (session ends
   * when the tab closes). See {@link TokenStore}.
   */
  tokenStore?: TokenStore
  /** Injectable `fetch` for tests. */
  fetchImpl?: FetchLike
}

export interface IdentityProviderProps {
  config: IdentityConfig
  children: ReactNode
}

/**
 * Wires the Goblin Guide hooks to a Barrin's Identity service. Must sit
 * under the host app's `QueryClientProvider` (TanStack Query is a peer
 * dependency).
 */
export function IdentityProvider({ config, children }: IdentityProviderProps) {
  const value = useMemo<IdentityContextValue>(() => {
    const tokenStore = config.tokenStore ?? createMemoryTokenStore()
    const client = createIdentityClient({
      serviceUrl: config.serviceUrl,
      tokenStore,
      fetchImpl: config.fetchImpl,
    })
    return { client, tokenStore }
  }, [config.serviceUrl, config.tokenStore, config.fetchImpl])

  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>
}
