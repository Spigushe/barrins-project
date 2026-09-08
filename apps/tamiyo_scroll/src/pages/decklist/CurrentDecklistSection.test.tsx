import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DISPLAY_PREF_CURRENT_DECKLIST_COLLAPSED } from '@/lib/displayPrefs'
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

// The S19 fold toggle uses the real `useLocalStorageFlag` (jsdom
// `localStorage`) — clear it between every test so a persisted collapse
// state can't leak into the S16 cases above or between S19 cases.
afterEach(() => {
  localStorage.clear()
})

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

describe('CurrentDecklistSection — S19 fold toggle', () => {
  beforeEach(() => {
    showChangeLog = false
    unmatchedCardTests = []
    decklistView = {
      commander_cards: [],
      library_cards: [{ category: 'other', count: 1, cards: [pendingCard('vis-1')] }],
      unparsed_lines: [],
    }
  })

  it('renders expanded by default, with a "Fold decklist" toggle', () => {
    const { container } = render(<CurrentDecklistSection />)

    const toggle = screen.getByRole('button', { name: 'Fold decklist' })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(container.querySelector('#current-decklist-body')).not.toBeNull()
  })

  it('collapses the decklist body when clicked and persists the choice', () => {
    const { container } = render(<CurrentDecklistSection />)

    fireEvent.click(screen.getByRole('button', { name: 'Fold decklist' }))

    expect(container.querySelector('#current-decklist-body')).toBeNull()
    expect(screen.getByRole('button', { name: 'Unfold decklist' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(localStorage.getItem(DISPLAY_PREF_CURRENT_DECKLIST_COLLAPSED)).toBe('true')
  })

  it('starts collapsed when the stored preference is set', () => {
    localStorage.setItem(DISPLAY_PREF_CURRENT_DECKLIST_COLLAPSED, 'true')

    const { container } = render(<CurrentDecklistSection />)

    expect(
      screen.getByRole('button', { name: 'Unfold decklist' }),
    ).toBeInTheDocument()
    expect(container.querySelector('#current-decklist-body')).toBeNull()
  })

  it('keeps the change-log block visible while collapsed', () => {
    localStorage.setItem(DISPLAY_PREF_CURRENT_DECKLIST_COLLAPSED, 'true')
    showChangeLog = true
    unmatchedCardTests = [
      {
        id: 'cl-1',
        removed_card_name: 'Counterspell',
        added_card_name: 'Mana Crypt',
        notes: 'shelved for now',
      },
    ]

    render(<CurrentDecklistSection />)

    expect(
      screen.getByText('Card change being considered in this version:'),
    ).toBeInTheDocument()
  })
})
