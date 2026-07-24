import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { emptyMatchDraft, MatchFormFields } from './MatchForm'

const createMetaDeckMutateAsync = vi.fn()

vi.mock('@/hooks/useMetaDecks', () => ({
  useCreateMetaDeck: () => ({ mutateAsync: createMetaDeckMutateAsync }),
}))

const personalDeckOptions = [{ id: 'deck-mine', name: 'Mono Red' }]
const metaDeckOptions = [{ id: 'deck-theirs', name: 'Azorius Control' }]

describe('MatchFormFields — opponent deck field', () => {
  it('selects an existing opponent deck', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <MatchFormFields
        draft={emptyMatchDraft('deck-mine')}
        onChange={onChange}
        personalDeckOptions={personalDeckOptions}
        metaDeckOptions={metaDeckOptions}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Opponent' }))
    await user.click(screen.getByText('Azorius Control'))

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ opponentDeckId: 'deck-theirs' }),
    )
  })

  it('creates a new opponent deck with tier/category and honest defaults for the rest', async () => {
    createMetaDeckMutateAsync.mockResolvedValue({ id: 'deck-new', name: 'Boros Energy' })
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <MatchFormFields
        draft={emptyMatchDraft('deck-mine')}
        onChange={onChange}
        personalDeckOptions={personalDeckOptions}
        metaDeckOptions={metaDeckOptions}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Opponent' }))
    await user.type(screen.getByPlaceholderText('Search or create…'), 'Boros Energy')
    await user.click(screen.getByText('Create "Boros Energy"'))

    // Quick-create dialog: only name (shown), tier, category are chosen —
    // no expected/top8/presence inputs (matches the Roster quick-add form).
    expect(screen.getByText('Boros Energy')).toBeInTheDocument()
    expect(screen.queryByText('Expected')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(createMetaDeckMutateAsync).toHaveBeenCalledWith({
      name: 'Boros Energy',
      tier: 1,
      category: 'midrange',
      decklist_notes: null,
      top8: 0,
      presence: 0,
      expected: 'as_expected',
      tests_status: null,
    })
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ opponentDeckId: 'deck-new' }),
    )
  })
})
