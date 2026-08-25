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
function pendingCard(pendingCardTestId: string) {
  return {
    qty: 1,
    name: 'Duress',
    status: 'pending' as const,
    mana_cost: null,
    type_line: null,
    text: null,
    keywords: [],
    scryfall_id: null,
    pending_added_card_name: 'Thoughtseize',
    pending_added_card_scryfall_id: null,
    pending_card_test_id: pendingCardTestId,
  }
}

let decklistView: {
  commander_cards: ReturnType<typeof pendingCard>[]
  library_cards: {
    category: string
    count: number
    cards: ReturnType<typeof pendingCard>[]
  }[]
  unparsed_lines: unknown[]
} = { commander_cards: [], library_cards: [], unparsed_lines: [] }

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
  useDecklistView: () => ({ data: decklistView }),
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

  it('omits a card test already shown inline as a pending decklist line (S17)', () => {
    showChangeLog = true
    unmatchedCardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Counterspell',
        added_card_name: 'Mana Crypt',
        notes: null,
      },
      {
        id: 'test-2',
        removed_card_name: 'Duress',
        added_card_name: 'Thoughtseize',
        notes: null,
      },
    ]
    // "test-1" now renders inline on the current decklist (its removed
    // card's line is pending) — only "test-2" (not reflected anywhere in
    // the current decklist) still needs the standalone block.
    decklistView = {
      commander_cards: [],
      library_cards: [{ category: 'other', count: 1, cards: [pendingCard('test-1')] }],
      unparsed_lines: [],
    }
    render(<CurrentDecklistSection />)

    expect(screen.getByText(heading)).toBeInTheDocument()
    expect(screen.getByText('- Duress')).toBeInTheDocument()
    expect(screen.queryByText('- Counterspell')).not.toBeInTheDocument()
  })

  it('hides the block when every unmatched card test is shown inline instead', () => {
    showChangeLog = true
    unmatchedCardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Counterspell',
        added_card_name: 'Mana Crypt',
        notes: null,
      },
    ]
    decklistView = {
      commander_cards: [],
      library_cards: [{ category: 'other', count: 1, cards: [pendingCard('test-1')] }],
      unparsed_lines: [],
    }
    render(<CurrentDecklistSection />)

    expect(screen.queryByText(heading)).not.toBeInTheDocument()
  })
})
