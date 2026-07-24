import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MetaDecksRosterSection } from './MetaDecksSections'

const decks = [
  { id: '1', name: 'Zenith Combo', tier: 1, category: 'combo', decklist_notes: null },
  { id: '2', name: 'Boros Aggro', tier: 0.5, category: 'aggro', decklist_notes: null },
  {
    id: '3',
    name: 'Azorius Control',
    tier: 1,
    category: 'control',
    decklist_notes: null,
  },
]

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ canEdit: false, activeDeckId: 'deck-1' }),
}))

vi.mock('@/hooks/useMetaDecks', () => ({
  useMetaDecks: () => ({ data: decks }),
  useCreateMetaDeck: () => ({ mutateAsync: vi.fn() }),
  useUpdateMetaDeck: () => ({ mutateAsync: vi.fn() }),
  useArchiveMetaDeck: () => ({ mutateAsync: vi.fn() }),
}))

describe('MetaDecksRosterSection sorting', () => {
  it('sorts by tier ascending, then name ascending within the same tier', () => {
    render(<MetaDecksRosterSection />)

    const nameInputs = screen
      .getAllByRole('textbox')
      .filter((_, index) => index % 2 === 0) // name input is first of the 2 inputs per row

    expect(nameInputs.map((input) => (input as HTMLInputElement).value)).toEqual([
      'Boros Aggro', // tier 0.5
      'Azorius Control', // tier 1, name asc
      'Zenith Combo', // tier 1, name asc
    ])
  })
})
