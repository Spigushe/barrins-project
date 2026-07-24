import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AppShell } from './AppShell'

let activePersonalDeckId: string | null = null

vi.mock('@/hooks/useAuth', () => ({
  useLogout: () => ({ mutateAsync: vi.fn() }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { active_personal_deck_id: activePersonalDeckId } }),
  useUpdateMySettings: () => ({ mutateAsync: vi.fn() }),
}))

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({ data: [] }),
  useCreatePersonalDeck: () => ({ mutateAsync: vi.fn() }),
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
