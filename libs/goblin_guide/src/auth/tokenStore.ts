import { createStore } from '../lib/store'

/**
 * Client-side token storage. Pluggable by design (Goblin Guide bootstrap
 * `G-05`): the default keeps both tokens in memory, so closing the tab ends
 * the session. A host that wants persistent sessions passes its own
 * implementation — e.g. one backed by a BFF that holds the refresh token in
 * an `HttpOnly` cookie — without any change to the rest of the library.
 */
export interface TokenStore {
  /** Current access token, or `null` when signed out. */
  getAccess: () => string | null
  /** Current refresh token, or `null` when there is nothing to refresh with. */
  getRefresh: () => string | null
  /** Persist a freshly issued pair (login, refresh, verify). */
  set: (tokens: { access_token: string; refresh_token: string }) => void
  /** Drop all token state (logout, dead session, account deletion). */
  clear: () => void
  /** Subscribe to changes — drives `useSyncExternalStore` in the hooks. */
  subscribe: (listener: () => void) => () => void
}

interface TokenState {
  access: string | null
  refresh: string | null
}

const EMPTY: TokenState = { access: null, refresh: null }

/** The default `TokenStore`: both tokens live in memory only. */
export function createMemoryTokenStore(): TokenStore {
  const store = createStore<TokenState>(EMPTY)
  return {
    getAccess: () => store.get().access,
    getRefresh: () => store.get().refresh,
    set: (tokens) => {
      store.set({ access: tokens.access_token, refresh: tokens.refresh_token })
    },
    clear: () => {
      store.set(EMPTY)
    },
    subscribe: store.subscribe,
  }
}
