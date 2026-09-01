import { type ReactNode, useEffect, useMemo, useRef, useState } from 'react'
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
  /**
   * Browser SPA cookie mode (ADR-18). When `true`, the refresh token is kept
   * in an `HttpOnly` cookie by Barrin's Identity and never touches JS; this
   * app holds only the in-memory access token. The identity service must run
   * with `REFRESH_COOKIE_ENABLED=true` and this app's origin in
   * `ALLOWED_ORIGINS`.
   */
  cookieMode?: boolean
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
  const cookieMode = config.cookieMode ?? false

  const { client, tokenStore } = useMemo(() => {
    const store = config.tokenStore ?? createMemoryTokenStore()
    return {
      client: createIdentityClient({
        serviceUrl: config.serviceUrl,
        tokenStore: store,
        fetchImpl: config.fetchImpl,
        cookieMode: config.cookieMode,
      }),
      tokenStore: store,
    }
  }, [config.serviceUrl, config.tokenStore, config.fetchImpl, config.cookieMode])

  // Cookie mode (ADR-18): the refresh token lives in an HttpOnly cookie, so on
  // a fresh page load nothing is in the in-memory store yet. Make one
  // `POST /auth/refresh` attempt to trade the cookie for an access token —
  // this is what makes a closed tab / F5 keep the session. Body mode never
  // persists across a reload by design, so it skips this entirely.
  const [isBootstrapping, setIsBootstrapping] = useState(cookieMode)
  const bootstrapped = useRef(false)
  useEffect(() => {
    if (!cookieMode || bootstrapped.current) return
    bootstrapped.current = true
    void client
      .refresh()
      .catch(() => {
        // No valid refresh cookie (never logged in, or it expired) — the
        // client has cleared any partial state; start on the login screen.
      })
      .finally(() => {
        setIsBootstrapping(false)
      })
  }, [client, cookieMode])

  const value = useMemo<IdentityContextValue>(
    () => ({ client, tokenStore, isBootstrapping }),
    [client, tokenStore, isBootstrapping],
  )

  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>
}
