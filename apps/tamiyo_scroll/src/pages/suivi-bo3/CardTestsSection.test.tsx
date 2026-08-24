import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import { CardTestsSection } from './CardTestsSection'

const createTestMutateAsync = vi.fn()
const updateTestMutateAsync = vi.fn()
const deleteTestMutateAsync = vi.fn()
const createEvaluationMutateAsync = vi.fn()
const updateEvaluationMutateAsync = vi.fn()
const deleteEvaluationMutateAsync = vi.fn()
let createTestError: unknown = null

vi.mock('@/hooks/useCardTests', () => ({
  useCardTests: () => ({ data: cardTests }),
  useCreateCardTest: () => ({
    mutateAsync: createTestMutateAsync,
    isPending: false,
    error: createTestError,
  }),
  useDeleteCardTest: () => ({ mutateAsync: deleteTestMutateAsync, isPending: false }),
  useUpdateCardTest: () => ({
    mutateAsync: updateTestMutateAsync,
    isPending: false,
    error: null,
  }),
  useCreateCardTestEvaluation: () => ({
    mutateAsync: createEvaluationMutateAsync,
    isPending: false,
    error: null,
  }),
  useUpdateCardTestEvaluation: () => ({
    mutateAsync: updateEvaluationMutateAsync,
    isPending: false,
    error: null,
  }),
  useDeleteCardTestEvaluation: () => ({
    mutateAsync: deleteEvaluationMutateAsync,
    isPending: false,
  }),
}))

const metaDecks = [
  { id: 'deck-a', name: 'Azorius Control', is_readonly: false },
  { id: 'deck-b', name: 'Boros Aggro', is_readonly: true },
]
let cardTests: {
  id: string
  removed_card_name: string
  added_card_name: string
  notes: string | null
  evaluations: {
    id: string
    opponent_deck_id: string
    rating: number
    notes: string | null
  }[]
}[] = []

vi.mock('@/hooks/useMetaDecks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useMetaDecks')>()
  return {
    ...actual,
    useMetaDecks: () => ({ data: metaDecks }),
  }
})

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-1', canEdit: true }),
}))

describe('CardTestsSection', () => {
  beforeEach(() => {
    cardTests = []
    createTestError = null
  })

  it('labels the table headers and create-form fields consistently', () => {
    render(<CardTestsSection />)

    const headerRow = screen.getAllByRole('columnheader')
    expect(headerRow.map((cell) => cell.textContent)).toEqual(
      expect.arrayContaining(['Removed Card', 'Added Card', 'Evaluations']),
    )
    expect(screen.getByLabelText('Removed Card')).toBeInTheDocument()
    expect(screen.getByLabelText('Added Card')).toBeInTheDocument()
    // S17: matchup/rating moved off the create form onto evaluations.
    expect(screen.queryByRole('button', { name: 'Match-up' })).not.toBeInTheDocument()
  })

  it('shows the backend error message inline after a failed create', () => {
    createTestError = new ApiError(
      400,
      "Removed card is not present in the deck's current decklist.",
    )
    render(<CardTestsSection />)

    expect(
      screen.getByText("Removed card is not present in the deck's current decklist."),
    ).toBeInTheDocument()
  })
})

describe('CardTestsSection — delete confirmation', () => {
  beforeEach(() => {
    cardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Duress',
        added_card_name: 'Lightning Bolt',
        notes: null,
        evaluations: [],
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

// S17: matchup/rating live on evaluations now, added from an expandable
// panel under each card log's row — same Popover+Command combobox
// pattern as before (search, select, "shared" sub-label, no inline
// create), just relocated.
describe('CardTestsSection — evaluations panel', () => {
  beforeEach(() => {
    createEvaluationMutateAsync.mockClear()
    updateEvaluationMutateAsync.mockClear()
  })

  it('expands to show the evaluations panel and add form', async () => {
    cardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Duress',
        added_card_name: 'Lightning Bolt',
        notes: null,
        evaluations: [],
      },
    ]
    const user = userEvent.setup()
    render(<CardTestsSection />)

    expect(screen.queryByText('No evaluations yet.')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^0/ }))

    expect(screen.getByText('No evaluations yet.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add evaluation' })).toBeInTheDocument()
  })

  it('searches and selects an opponent deck in the add-evaluation form', async () => {
    cardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Duress',
        added_card_name: 'Lightning Bolt',
        notes: null,
        evaluations: [],
      },
    ]
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.click(screen.getByRole('button', { name: /^0/ }))
    await user.click(screen.getByRole('button', { name: 'Match-up' }))
    await user.type(screen.getByPlaceholderText('Search…'), 'Azorius')
    await user.click(screen.getByText('Azorius Control'))

    expect(screen.getByRole('button', { name: 'Match-up' })).toHaveTextContent(
      'Azorius Control',
    )

    await user.click(screen.getByRole('button', { name: 'Add evaluation' }))
    expect(createEvaluationMutateAsync).toHaveBeenCalledWith({
      testId: 'test-1',
      payload: { opponent_deck_id: 'deck-a', rating: 3, notes: null },
    })
  })

  it('shows the shared sub-label for a readonly deck, without offering inline create', async () => {
    cardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Duress',
        added_card_name: 'Lightning Bolt',
        notes: null,
        evaluations: [],
      },
    ]
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.click(screen.getByRole('button', { name: /^0/ }))
    await user.click(screen.getByRole('button', { name: 'Match-up' }))

    expect(screen.getByText('shared — tap to add to your roster')).toBeInTheDocument()
    expect(screen.queryByText(/^Create "/)).not.toBeInTheDocument()
  })

  it('lists an existing evaluation and lets it be edited', async () => {
    cardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Duress',
        added_card_name: 'Lightning Bolt',
        notes: null,
        evaluations: [
          { id: 'eval-1', opponent_deck_id: 'deck-a', rating: 3, notes: null },
        ],
      },
    ]
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.click(screen.getByRole('button', { name: /^1/ }))
    expect(screen.getByText('Azorius Control')).toBeInTheDocument()

    const editButtons = screen.getAllByRole('button', { name: 'Edit' })
    await user.click(editButtons[editButtons.length - 1])
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateEvaluationMutateAsync).toHaveBeenCalledWith({
      testId: 'test-1',
      evaluationId: 'eval-1',
      payload: { opponent_deck_id: 'deck-a', rating: 3, notes: null },
    })
  })
})
