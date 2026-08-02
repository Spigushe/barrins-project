import type { ReactElement } from 'react'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, it } from 'vitest'
import { DecklistTab } from '@/pages/DecklistTab'
import { MetagameTab } from '@/pages/MetagameTab'
import { SuiviBo3Tab } from '@/pages/SuiviBo3Tab'
import { resetDemoStore } from '../demoStore'
import { DemoModeProvider } from '../DemoModeProvider'
import {
  expectDecklistTabRendersFixtureData,
  expectMetagameTabRendersFixtureData,
  expectSuiviBo3TabRendersFixtureData,
} from './reuseAssertions'

/**
 * Renders the three unmodified tab components through the real, production
 * data path: real `usePersonalDecks`/`useMatches`/etc. hooks, real
 * `src/api/*.ts` modules, real `apiRequest` — with only `window.fetch`
 * intercepted (`DemoModeProvider` → `fetchInterceptor.ts`) to serve demo
 * data instead of `barrins_api`. No network call happens (there is no
 * fallback to the original `fetch`).
 *
 * See `reuse.mocked-backend.test.tsx` for the other half of the "reuse,
 * don't fork" check: the same tabs, the same expectations, fed the same
 * fixture data by a different mechanism.
 */

beforeEach(() => {
  localStorage.clear()
  resetDemoStore()
})

function renderInDemoMode(ui: ReactElement) {
  return render(
    <MemoryRouter>
      <DemoModeProvider>{ui}</DemoModeProvider>
    </MemoryRouter>,
  )
}

describe('demo mode: MetagameTab', () => {
  it('renders the seeded metagame data, unmodified', async () => {
    const view = renderInDemoMode(<MetagameTab />)
    await expectMetagameTabRendersFixtureData(view)
  })
})

describe('demo mode: SuiviBo3Tab', () => {
  it('renders the seeded match log, unmodified', async () => {
    const view = renderInDemoMode(<SuiviBo3Tab />)
    await expectSuiviBo3TabRendersFixtureData(view)
  })
})

describe('demo mode: DecklistTab', () => {
  it('renders the seeded decklist, unmodified', async () => {
    const view = renderInDemoMode(<DecklistTab />)
    await expectDecklistTabRendersFixtureData(view)
  })
})
