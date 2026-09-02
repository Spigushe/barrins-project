import type { ReactNode } from 'react'
import { IdentityProvider } from '@barrins/goblin-guide'

/**
 * Wraps children in a body-mode `IdentityProvider` for tests that render a
 * component using Goblin Guide hooks (`useCurrentUser`, `useIdentity`, …)
 * without going through the real app tree. Body mode ⇒ no on-mount
 * `refresh()` call, `isBootstrapping` is always `false`, and with no token
 * in the store `useCurrentUser()` stays disabled and resolves to
 * `{ data: undefined }` — the same state the demo path sees in production.
 *
 * Must sit under a `QueryClientProvider` (TanStack Query is a peer dep).
 */
export function TestIdentityProvider({ children }: { children: ReactNode }) {
  return (
    <IdentityProvider config={{ serviceUrl: 'http://localhost:8001' }}>
      {children}
    </IdentityProvider>
  )
}
