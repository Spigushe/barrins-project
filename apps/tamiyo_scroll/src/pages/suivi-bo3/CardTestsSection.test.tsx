import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CardTestsSection } from './CardTestsSection'

vi.mock('@/hooks/useCardTests', () => ({
  useCardTests: () => ({ data: [] }),
  useCreateCardTest: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteCardTest: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateCardTest: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/useMetaDecks', () => ({
  useMetaDecks: () => ({ data: [] }),
}))

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({ data: { display_name: 'Alice', email: 'alice@example.com' } }),
}))

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-1', canEdit: true }),
}))

describe('CardTestsSection', () => {
  it('prefills the tester input with the current user display name', () => {
    render(<CardTestsSection />)

    expect(screen.getByLabelText('Pseudo')).toHaveValue('Alice')
  })
})
