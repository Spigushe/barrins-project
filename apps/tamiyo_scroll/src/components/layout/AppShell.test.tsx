import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AppShell } from './AppShell'

let activePersonalDeckId: string | null = null
let currentUser: { display_name: string | null; email: string } | undefined = undefined

vi.mock('@/hooks/useAuth', () => ({
  useLogout: () => ({ mutateAsync: vi.fn() }),
  useCurrentUser: () => ({ data: currentUser }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { active_personal_deck_id: activePersonalDeckId } }),
  useUpdateMySettings: () => ({ mutateAsync: vi.fn() }),
}))

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({ data: [] }),
  useCreatePersonalDeck: () => ({ mutateAsync: vi.fn() }),
  useArchivePersonalDeck: () => ({ mutateAsync: vi.fn() }),
}))

function renderAppShell() {
  return render(
    <MemoryRouter>
      <AppShell>
        <div>page content</div>
      </AppShell>
    </MemoryRouter>,
  )
}

describe('AppShell tab visibility', () => {
  it('hides the three tabs when no personal deck is selected', () => {
    activePersonalDeckId = null
    renderAppShell()
    expect(screen.queryByText('Metagame')).not.toBeInTheDocument()
    expect(screen.queryByText('BO3 Tracking')).not.toBeInTheDocument()
    expect(screen.queryByText('My decklist')).not.toBeInTheDocument()
  })

  it('shows the three tabs once a personal deck is selected', () => {
    activePersonalDeckId = 'deck-1'
    renderAppShell()
    expect(screen.getByText('Metagame')).toBeInTheDocument()
    expect(screen.getByText('BO3 Tracking')).toBeInTheDocument()
    expect(screen.getByText('My decklist')).toBeInTheDocument()
  })
})

describe('AppShell welcome message', () => {
  it('greets the user by display name when set', () => {
    currentUser = { display_name: 'Jace', email: 'jace@example.com' }
    renderAppShell()
    expect(screen.getByText('Welcome, Jace')).toBeInTheDocument()
  })

  it('falls back to the email when no display name is set', () => {
    currentUser = { display_name: null, email: 'jace@example.com' }
    renderAppShell()
    expect(screen.getByText('Welcome, jace@example.com')).toBeInTheDocument()
  })

  it('shows nothing while the current user has not loaded yet', () => {
    currentUser = undefined
    renderAppShell()
    expect(screen.queryByText(/Welcome,/)).not.toBeInTheDocument()
  })
})
