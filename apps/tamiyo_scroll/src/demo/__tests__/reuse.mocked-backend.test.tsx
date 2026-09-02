import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, it, vi } from 'vitest'
import { ActiveDeckContext } from '@/contexts/active-deck-context'
import { TestIdentityProvider } from '@/test/identity'
import { DecklistTab } from '@/pages/DecklistTab'
import { MetagameTab } from '@/pages/MetagameTab'
import { SuiviBo3Tab } from '@/pages/SuiviBo3Tab'
import { resetDemoStore } from '../demoStore'
import fixtures from '../fixtures.json'
import {
  expectDecklistTabRendersFixtureData,
  expectMetagameTabRendersFixtureData,
  expectSuiviBo3TabRendersFixtureData,
} from './reuseAssertions'

/**
 * The other half of the "reuse, don't fork" check (S7) — see
 * `reuse.demo-mode.test.tsx`. Here `src/api/*.ts` itself is swapped
 * (`vi.mock`) for the demo data-source module, standing in for "a real
 * backend that happens to return this same data" — no `DemoModeProvider`,
 * no fetch interception, just the real hooks talking to a plain
 * `QueryClientProvider` + `ActiveDeckContext`, exactly like a signed-in
 * session would. Same tab components, same expectations
 * (`./reuseAssertions.ts`) as the demo-mode test — if either file needed
 * different assertions to pass, that would mean the tabs behave differently
 * depending on how their data arrived.
 */

vi.mock('@/api/personalDecks', () => import('../api/personalDecks'))
vi.mock('@/api/matches', () => import('../api/matches'))
vi.mock('@/api/metaDecks', () => import('../api/metaDecks'))
vi.mock('@/api/cardTests', () => import('../api/cardTests'))
vi.mock('@/api/stats', () => import('../api/stats'))
vi.mock('@/api/sessions', () => import('../api/sessions'))

const DEMO_DECK_ID = fixtures.personalDecks[0].id

beforeEach(() => {
  localStorage.clear()
  resetDemoStore()
})

function renderViaMockedBackend(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <TestIdentityProvider>
          <ActiveDeckContext.Provider
            value={{ activeDeckId: DEMO_DECK_ID, canEdit: true }}
          >
            {ui}
          </ActiveDeckContext.Provider>
        </TestIdentityProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('mocked backend: MetagameTab', () => {
  it('renders the seeded metagame data, unmodified', async () => {
    const view = renderViaMockedBackend(<MetagameTab />)
    await expectMetagameTabRendersFixtureData(view)
  })
})

describe('mocked backend: SuiviBo3Tab', () => {
  it('renders the seeded match log, unmodified', async () => {
    const view = renderViaMockedBackend(<SuiviBo3Tab />)
    await expectSuiviBo3TabRendersFixtureData(view)
  })
})

describe('mocked backend: DecklistTab', () => {
  it('renders the seeded decklist, unmodified', async () => {
    const view = renderViaMockedBackend(<DecklistTab />)
    await expectDecklistTabRendersFixtureData(view)
  })
})
