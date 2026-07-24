import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PersonalDeckSelector } from './PersonalDeckSelector'

const updateSettingsMutateAsync = vi.fn()
const createDeckMutateAsync = vi.fn()

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({
    data: [
      { id: 'deck-1', name: 'Mono Red', archived_at: null, created_at: '' },
      { id: 'deck-2', name: 'Azorius Control', archived_at: null, created_at: '' },
    ],
  }),
  useCreatePersonalDeck: () => ({ mutateAsync: createDeckMutateAsync }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { active_personal_deck_id: 'deck-1' } }),
  useUpdateMySettings: () => ({ mutateAsync: updateSettingsMutateAsync }),
}))

describe('PersonalDeckSelector', () => {
  it('shows the active deck name in the trigger', () => {
    render(<PersonalDeckSelector />)
    expect(screen.getByText('Mono Red')).toBeInTheDocument()
  })

  it('selects an existing deck from the list', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.click(screen.getByText('Azorius Control'))

    expect(updateSettingsMutateAsync).toHaveBeenCalledWith({
      active_personal_deck_id: 'deck-2',
    })
  })

  it('creates and auto-selects a new deck when no exact match exists', async () => {
    createDeckMutateAsync.mockResolvedValue({
      id: 'deck-3',
      name: 'Boros Aggro',
      archived_at: null,
      created_at: '',
    })
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.type(
      screen.getByPlaceholderText('Search or create a deck…'),
      'Boros Aggro',
    )
    await user.click(screen.getByText('Create "Boros Aggro"'))

    expect(createDeckMutateAsync).toHaveBeenCalledWith('Boros Aggro')
    expect(updateSettingsMutateAsync).toHaveBeenCalledWith({
      active_personal_deck_id: 'deck-3',
    })
  })

  it('does not offer to create a deck that already exists by that name', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.type(screen.getByPlaceholderText('Search or create a deck…'), 'Mono Red')

    expect(screen.queryByText('Create "Mono Red"')).not.toBeInTheDocument()
  })
})
