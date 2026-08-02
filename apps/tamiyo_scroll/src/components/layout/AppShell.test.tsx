import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AppShell } from './AppShell'

let activePersonalDeckId: string | null = null
let currentUser: { display_name: string | null; email: string } | undefined = undefined

vi.mock('@/hooks/useAuth', () => ({
  useLogout: () => ({ mutateAsync: vi.fn() }),
  useCurrentUser: () => ({ data: currentUser }),
  useUpdateProfile: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { active_personal_deck_id: activePersonalDeckId } }),
  useUpdateMySettings: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({ data: [] }),
  useCreatePersonalDeck: () => ({ mutateAsync: vi.fn() }),
  useArchivePersonalDeck: () => ({ mutateAsync: vi.fn() }),
  useRenamePersonalDeck: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDownloadDeckReport: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/useTeams', () => ({
  useMyTeams: () => ({ data: [] }),
  useTeamDecks: () => ({ data: [] }),
  useDownloadTeamDeckReport: () => ({ mutate: vi.fn(), isPending: false }),
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
  it('hides the tabs when no personal deck is selected', () => {
    activePersonalDeckId = null
    renderAppShell()
    expect(screen.queryByText('Metagame')).not.toBeInTheDocument()
    expect(screen.queryByText('BO3 Tracking')).not.toBeInTheDocument()
    expect(screen.queryByText('My decklist')).not.toBeInTheDocument()
    expect(screen.queryByText('Teams')).not.toBeInTheDocument()
  })

  it('shows the tabs once a personal deck is selected', () => {
    activePersonalDeckId = 'deck-1'
    renderAppShell()
    expect(screen.getByText('Metagame')).toBeInTheDocument()
    expect(screen.getByText('BO3 Tracking')).toBeInTheDocument()
    expect(screen.getByText('My decklist')).toBeInTheDocument()
    expect(screen.getByText('Teams')).toBeInTheDocument()
  })
})

describe('AppShell main content', () => {
  it('hides the page content when no personal deck is selected', () => {
    activePersonalDeckId = null
    renderAppShell()
    expect(screen.queryByText('page content')).not.toBeInTheDocument()
    expect(
      screen.getByText('Create or select a personal deck above to get started.'),
    ).toBeInTheDocument()
  })

  it('shows the page content once a personal deck is selected', () => {
    activePersonalDeckId = 'deck-1'
    renderAppShell()
    expect(screen.getByText('page content')).toBeInTheDocument()
    expect(
      screen.queryByText('Create or select a personal deck above to get started.'),
    ).not.toBeInTheDocument()
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
