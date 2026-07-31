import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { NewMatchSection } from './NewMatchSection'

let activeDeckId: string | null = 'deck-1'

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId, canEdit: true }),
}))

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({
    data: [
      { id: 'deck-1', name: "King T'Challa", archived_at: null, created_at: '' },
      { id: 'deck-2', name: 'Spider-Man 2099', archived_at: null, created_at: '' },
    ],
  }),
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
})
