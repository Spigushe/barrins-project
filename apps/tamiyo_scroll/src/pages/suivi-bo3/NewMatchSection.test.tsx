import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { NewMatchSection } from './NewMatchSection'

let activeDeckId: string | null = 'deck-1'

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId, canEdit: true }),
}))

const updateDeckMutateAsync = vi.fn()

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({
    data: [
      {
        id: 'deck-1',
        name: "King T'Challa",
        game: 'magic',
        category: 'midrange',
        archived_at: null,
        created_at: '',
      },
      {
        id: 'deck-2',
        name: 'Spider-Man 2099',
        game: null,
        category: null,
        archived_at: null,
        created_at: '',
      },
    ],
  }),
  useUpdatePersonalDeck: () => ({ mutateAsync: updateDeckMutateAsync, isPending: false }),
}))

vi.mock('@/hooks/useMetaDecks', () => ({
  useMetaDecks: () => ({ data: [] }),
  useCreateMetaDeck: () => ({ mutateAsync: vi.fn() }),
}))

vi.mock('@/hooks/useMatches', () => ({
  useCreateMatch: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/useSessions', () => ({
  useSessions: () => ({ data: [] }),
  useCreateSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

describe('NewMatchSection', () => {
  it("follows the header's active personal deck when it changes", () => {
    activeDeckId = 'deck-1'
    const { rerender } = render(<NewMatchSection />)
    expect(screen.getByText("King T'Challa")).toBeInTheDocument()

    activeDeckId = 'deck-2'
    rerender(<NewMatchSection />)
    expect(screen.getByText('Spider-Man 2099')).toBeInTheDocument()
    expect(screen.queryByText("King T'Challa")).not.toBeInTheDocument()
  })

  it('allows logging a match on a fully set-up deck', () => {
    activeDeckId = 'deck-1'
    render(<NewMatchSection />)
    expect(screen.queryByText(/set "King T'Challa"'s game and archetype/i)).not
      .toBeInTheDocument()
  })

  it('blocks logging a match on a deck missing game/category (S10/S11)', () => {
    activeDeckId = 'deck-2'
    render(<NewMatchSection />)
    expect(
      screen.getByText(/set "Spider-Man 2099"'s game and archetype/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save the game' })).toBeDisabled()
  })
})
