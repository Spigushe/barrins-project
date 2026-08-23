import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CardTestsSection } from './CardTestsSection'

const createTestMutateAsync = vi.fn()
const updateTestMutateAsync = vi.fn()
const deleteTestMutateAsync = vi.fn()

vi.mock('@/hooks/useCardTests', () => ({
  useCardTests: () => ({ data: cardTests }),
  useCreateCardTest: () => ({ mutateAsync: createTestMutateAsync, isPending: false }),
  useDeleteCardTest: () => ({ mutateAsync: deleteTestMutateAsync, isPending: false }),
  useUpdateCardTest: () => ({ mutateAsync: updateTestMutateAsync, isPending: false }),
}))

const metaDecks = [
  { id: 'deck-a', name: 'Azorius Control', is_readonly: false },
  { id: 'deck-b', name: 'Boros Aggro', is_readonly: true },
]
let cardTests: {
  id: string
  tester: string
  card_name: string
  opponent_deck_id: string | null
  rating: number
  notes: string | null
}[] = []

vi.mock('@/hooks/useMetaDecks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useMetaDecks')>()
  return {
    ...actual,
    useMetaDecks: () => ({ data: metaDecks }),
  }
})

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({ data: { display_name: 'Alice', email: 'alice@example.com' } }),
}))

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-1', canEdit: true }),
}))

describe('CardTestsSection', () => {
  it('prefills the tester input with the current user display name', () => {
    cardTests = []
    render(<CardTestsSection />)

    expect(screen.getByLabelText('Nickname')).toHaveValue('Alice')
  })
})

describe('CardTestsSection — delete confirmation', () => {
  beforeEach(() => {
    cardTests = [
      {
        id: 'test-1',
        tester: 'Alice',
        card_name: 'Lightning Bolt',
        opponent_deck_id: null,
        rating: 3,
        notes: null,
      },
    ]
    deleteTestMutateAsync.mockClear()
  })

  it('asks for confirmation before deleting, without deleting immediately', async () => {
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.click(screen.getByRole('button', { name: '✕' }))

    expect(deleteTestMutateAsync).not.toHaveBeenCalled()
    expect(screen.getByText('Delete "Lightning Bolt"?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(deleteTestMutateAsync).toHaveBeenCalledWith('test-1')
  })

  it('cancels without deleting', async () => {
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.click(screen.getByRole('button', { name: '✕' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(deleteTestMutateAsync).not.toHaveBeenCalled()
    expect(screen.queryByText('Delete "Lightning Bolt"?')).not.toBeInTheDocument()
  })
})

// S12 item 2: the Match-up select is rebuilt on the same Popover+Command
// combobox pattern as `OpponentDeckField` — search, select, and a
// "shared" sub-label, no inline create (out of scope per the doc).
describe('CardTestsSection — Match-up combobox parity', () => {
  it('searches and selects an opponent deck in the create form', async () => {
    cardTests = []
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.click(screen.getByRole('button', { name: 'Match-up' }))
    await user.type(screen.getByPlaceholderText('Search…'), 'Azorius')
    await user.click(screen.getByText('Azorius Control'))

    expect(screen.getByRole('button', { name: 'Match-up' })).toHaveTextContent(
      'Azorius Control',
    )
  })

  it('shows the shared sub-label for a readonly deck, without offering inline create', async () => {
    cardTests = []
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.click(screen.getByRole('button', { name: 'Match-up' }))

    expect(
      screen.getByText('shared — tap to add to your roster'),
    ).toBeInTheDocument()
    expect(screen.queryByText(/^Create "/)).not.toBeInTheDocument()
  })

  it('uses the same combobox for the edit row, pre-filled with the current matchup', async () => {
    cardTests = [
      {
        id: 'test-1',
        tester: 'Alice',
        card_name: 'Lightning Bolt',
        opponent_deck_id: 'deck-a',
        rating: 3,
        notes: null,
      },
    ]
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.click(screen.getByRole('button', { name: 'Edit' }))

    const matchupButtons = screen.getAllByRole('button', { name: 'Match-up' })
    // One in the create form, one in the now-editing row.
    expect(matchupButtons).toHaveLength(2)
    expect(matchupButtons[1]).toHaveTextContent('Azorius Control')
  })
})
