import { type ReactNode, useEffect, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ActiveDeckContext } from '@/contexts/active-deck-context'
import { resetDemoStore } from './demoStore'
import fixtures from './fixtures.json'
import { installDemoFetch } from './fetchInterceptor'

// The one personal deck the demo tour is built around — see fixtures.json.
const DEMO_ACTIVE_DECK_ID: string = fixtures.personalDecks[0].id

function createDemoQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  })
}

/**
 * Supplies the demo data source to `MetagameTab`/`SuiviBo3Tab`/`DecklistTab`
 * in place of `barrins_api`, without either of them (or the hooks they use)
 * knowing the difference — see `fetchInterceptor.ts` for how the swap
 * actually works.
 *
 * Also stands in for `AppShell`'s `ActiveDeckContext` (the tabs read
 * `useActiveDeck()` for the selected personal deck and edit permission) with
 * a single fixed deck, since the demo has no deck switcher.
 */
export function DemoModeProvider({ children }: { children: ReactNode }) {
  // Fresh QueryClient per mount: never shares a cache with the real app's
  // `queryClient` (see `main.tsx`), and never carries stale demo data across
  // a visit that leaves and re-enters `/demo` without a full page reload.
  const [queryClient] = useState(createDemoQueryClient)

  // Installed via a lazy `useState` initializer rather than `useEffect`:
  // React runs a child's effects before its parent's, so `MetagameTab`'s
  // hooks could otherwise fire their first (real, un-intercepted) fetch
  // before this provider's own effect had a chance to install the router.
  // A lazy initializer runs synchronously during this component's own
  // render, before any child even mounts.
  const [uninstallDemoFetch] = useState(() => {
    resetDemoStore()
    return installDemoFetch()
  })

  useEffect(() => uninstallDemoFetch, [uninstallDemoFetch])

  return (
    <QueryClientProvider client={queryClient}>
      <ActiveDeckContext.Provider
        value={{ activeDeckId: DEMO_ACTIVE_DECK_ID, canEdit: true }}
      >
        {children}
      </ActiveDeckContext.Provider>
    </QueryClientProvider>
  )
}
