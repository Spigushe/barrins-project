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
  removed_card_scryfall_id?: string | null
  added_card_scryfall_id?: string | null
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

let decklistView: {
  commander_cards: { name: string }[]
  library_cards: { cards: { name: string }[] }[]
  unparsed_lines: unknown[]
} = { commander_cards: [], library_cards: [], unparsed_lines: [] }

vi.mock('@/hooks/useDecklistVersions', () => ({
  useDecklistView: () => ({ data: decklistView }),
}))

let addedCardSearchResult: { data: string[]; isFetching: boolean } = {
  data: [],
  isFetching: false,
}

vi.mock('@/hooks/useCards', () => ({
  CARD_NAME_SEARCH_MIN_LENGTH: 3,
  useCardNameSearch: () => addedCardSearchResult,
}))

let mySettings: { validate_added_card_exists: boolean } = {
  validate_added_card_exists: false,
}

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: mySettings }),
}))

describe('CardTestsSection', () => {
  beforeEach(() => {
    cardTests = []
    createTestError = null
    decklistView = { commander_cards: [], library_cards: [], unparsed_lines: [] }
    addedCardSearchResult = { data: [], isFetching: false }
    mySettings = { validate_added_card_exists: false }
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

// S17 item 3 follow-up: the card log's own Removed/Added Card cells
// hover-preview an image the same way a pending decklist line does.
describe('CardTestsSection — card name hover previews', () => {
  beforeEach(() => {
    createTestError = null
    decklistView = { commander_cards: [], library_cards: [], unparsed_lines: [] }
    addedCardSearchResult = { data: [], isFetching: false }
  })

  it('shows the added card image on hover when its scryfall id resolved', async () => {
    cardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Duress',
        added_card_name: 'Lightning Bolt',
        removed_card_scryfall_id: null,
        added_card_scryfall_id: 'bolt-scryfall-id',
        notes: null,
        evaluations: [],
      },
    ]
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.hover(screen.getByText('Lightning Bolt'))
    expect(await screen.findByAltText('Lightning Bolt')).toBeInTheDocument()
  })

  it('renders a plain name with no hover preview when unresolved', () => {
    cardTests = [
      {
        id: 'test-1',
        removed_card_name: 'Some Homebrew Card',
        added_card_name: 'Lightning Bolt',
        removed_card_scryfall_id: null,
        added_card_scryfall_id: null,
        notes: null,
        evaluations: [],
      },
    ]
    render(<CardTestsSection />)

    const name = screen.getByText('Some Homebrew Card')
    expect(name).not.toHaveClass('underline')
  })
})

// S17 item 2: name-validation UX -- Removed-Card suggests from the
// already-fetched current decklist, Added-Card suggests from the new
// partial-match search endpoint, and free text stays valid either way.
describe('CardTestsSection — name dropdowns', () => {
  beforeEach(() => {
    cardTests = []
    createTestError = null
  })

  it('suggests a removed-card name from the current decklist and fills it in on selection', async () => {
    decklistView = {
      commander_cards: [],
      library_cards: [{ cards: [{ name: 'Lightning Bolt' }, { name: 'Duress' }] }],
      unparsed_lines: [],
    }
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.type(screen.getByLabelText('Removed Card'), 'light')
    await user.click(screen.getByText('Lightning Bolt'))

    expect(screen.getByLabelText('Removed Card')).toHaveValue('Lightning Bolt')
  })

  it('keeps free-text entry valid when the removed card has no matching suggestion', async () => {
    decklistView = {
      commander_cards: [],
      library_cards: [{ cards: [{ name: 'Lightning Bolt' }] }],
      unparsed_lines: [],
    }
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.type(screen.getByLabelText('Removed Card'), 'Some Custom Card')

    expect(screen.getByLabelText('Removed Card')).toHaveValue('Some Custom Card')
    expect(screen.queryByText('Lightning Bolt')).not.toBeInTheDocument()
  })

  it('suggests an added-card name from the search endpoint and fills it in on selection', async () => {
    addedCardSearchResult = { data: ['Thoughtseize'], isFetching: false }
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.type(screen.getByLabelText('Added Card'), 'thou')
    await user.click(screen.getByText('Thoughtseize'))

    expect(screen.getByLabelText('Added Card')).toHaveValue('Thoughtseize')
  })

  it('shows a not-found hint once the added-card search comes back empty and validation is on', async () => {
    addedCardSearchResult = { data: [], isFetching: false }
    mySettings = { validate_added_card_exists: true }
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.type(screen.getByLabelText('Added Card'), 'xyz')

    expect(
      await screen.findByText('No matching card found — you can still save this name.'),
    ).toBeInTheDocument()
  })

  it('hides the not-found hint when "Validate added card exists" is off', async () => {
    addedCardSearchResult = { data: [], isFetching: false }
    mySettings = { validate_added_card_exists: false }
    const user = userEvent.setup()
    render(<CardTestsSection />)

    await user.type(screen.getByLabelText('Added Card'), 'xyz')

    expect(
      screen.queryByText('No matching card found — you can still save this name.'),
    ).not.toBeInTheDocument()
  })
})
