import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CurrentDecklistSection } from './CurrentDecklistSection'

const versions = [
  {
    id: 'v1',
    personal_deck_id: 'deck-1',
    version: 1,
    content: '4 Lightning Bolt',
    source: 'manual' as const,
    created_at: '2026-08-24T10:00:00+00:00',
  },
]

let showChangeLog = true
let unmatchedCardTests: {
  id: string
  removed_card_name: string
  added_card_name: string
  notes: string | null
}[] = []

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-1', canEdit: true }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { show_decklist_change_log: showChangeLog } }),
}))

vi.mock('@/hooks/useCardTests', () => ({
  useCardTestChangeLog: () => ({ data: unmatchedCardTests }),
}))

vi.mock('@/hooks/useDecklistVersions', () => ({
  useDecklistVersions: () => ({ data: versions }),
  useDecklistView: () => ({
    data: { commander_cards: [], library_cards: [], unparsed_lines: [] },
  }),
}))

vi.mock('@/hooks/usePersonalDecks', () => ({
  useDownloadDeckReport: () => ({ mutate: vi.fn(), isPending: false }),
  usePersonalDecks: () => ({ data: [] }),
}))

describe('CurrentDecklistSection — S16 untracked card tests', () => {
  const heading = 'Card change being considered in this version:'

  it('is hidden when the change-log setting is off', () => {
    showChangeLog = false
    unmatchedCardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Counterspell',
        added_card_name: 'Mana Crypt',
        notes: null,
      },
    ]
    render(<CurrentDecklistSection />)

    expect(screen.queryByText(heading)).not.toBeInTheDocument()
  })

  it('hides the block entirely when there are no unmatched card tests', () => {
    showChangeLog = true
    unmatchedCardTests = []
    render(<CurrentDecklistSection />)

    expect(screen.queryByText(heading)).not.toBeInTheDocument()
  })

  it('lists an unmatched card test with its note', () => {
    showChangeLog = true
    unmatchedCardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Counterspell',
        added_card_name: 'Mana Crypt',
        notes: 'never actually made the cut',
      },
    ]
    render(<CurrentDecklistSection />)

    expect(screen.getByText(heading)).toBeInTheDocument()
    expect(screen.getByText('- Counterspell')).toBeInTheDocument()
    expect(screen.getByText('+ Mana Crypt')).toBeInTheDocument()
    expect(screen.getByText('never actually made the cut')).toBeInTheDocument()
  })

  it('shows a dash placeholder when the unmatched card test has no notes', () => {
    showChangeLog = true
    unmatchedCardTests = [
      {
        id: 'test-2',
        removed_card_name: 'Duress',
        added_card_name: 'Thoughtseize',
        notes: null,
      },
    ]
    render(<CurrentDecklistSection />)

    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
