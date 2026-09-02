import { createIdentityClient, createMemoryTokenStore } from '@barrins/goblin-guide'
import { IDENTITY_COOKIE_MODE, IDENTITY_SERVICE_URL } from '@/config'

/**
 * Module singletons shared by the identity provider (`main.tsx`) and the
 * `barrins_api` data client (`api/client.ts`).
 *
 * `IdentityProvider` is handed this same `tokenStore`, so the access token it
 * obtains on login / cookie-mode restore is the one `api/client.ts` reads when
 * it puts a `Bearer` on every `barrins_api` request. `identityClient` here is
 * only used for the silent `refresh()` on a `401` — the provider drives login,
 * `me`, logout, etc. through its own internal client bound to the same store.
 */
export const identityTokenStore = createMemoryTokenStore()

export const identityClient = createIdentityClient({
  serviceUrl: IDENTITY_SERVICE_URL,
  tokenStore: identityTokenStore,
  cookieMode: IDENTITY_COOKIE_MODE,
})
