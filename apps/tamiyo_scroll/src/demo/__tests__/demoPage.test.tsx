import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { DemoPage } from '../DemoPage'
import { resetDemoStore } from '../demoStore'

beforeEach(() => {
  localStorage.clear()
  resetDemoStore()
})

function renderDemoPage() {
  return render(
    <MemoryRouter initialEntries={['/demo']}>
      <DemoPage />
    </MemoryRouter>,
  )
}

describe('DemoPage tabs', () => {
  it('lists all 5 tabs in the same order as the real app (AppShell.TABS)', () => {
    renderDemoPage()
    const tabs = screen.getAllByRole('tab').map((tab) => tab.textContent)
    expect(tabs).toEqual(['BO3 Tracking', 'Metagame', 'My decklist', 'Sessions', 'Teams'])
  })

  it('switching to Sessions and Teams renders their content locally, without any real navigation', async () => {
    const user = userEvent.setup()
    renderDemoPage()

    await user.click(screen.getByRole('tab', { name: 'Sessions' }))
    await screen.findByText('Store Championship')

    // Regression test: `TeamsTab`/`TeamPage` navigate via `/team/*`
    // routes wrapped in `ProtectedRoute`, which bounce an unauthenticated
    // visitor to `/login`. `DemoTeamsSection` must render the same content
    // via local state instead — this must NOT redirect away from /demo.
    await user.click(screen.getByRole('tab', { name: 'Teams' }))
    await screen.findByText('The Cabal (Demo)')
    await screen.findByText('Members')
    expect(screen.queryByText(/log in/i, { selector: 'h1, h2' })).not.toBeInTheDocument()

    // Still on the demo tab strip, not redirected anywhere else.
    expect(screen.getAllByRole('tab')).toHaveLength(5)
  })
})
