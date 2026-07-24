import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PersonalDeckSelector } from './PersonalDeckSelector'

const updateSettingsMutateAsync = vi.fn()
const createDeckMutateAsync = vi.fn()
const archiveDeckMutateAsync = vi.fn()

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({
    data: [
      { id: 'deck-1', name: 'Mono Red', archived_at: null, created_at: '' },
      { id: 'deck-2', name: 'Azorius Control', archived_at: null, created_at: '' },
      { id: 'deck-4', name: 'Zendikar Ramp', archived_at: null, created_at: '' },
    ],
  }),
  useCreatePersonalDeck: () => ({ mutateAsync: createDeckMutateAsync }),
  useArchivePersonalDeck: () => ({ mutateAsync: archiveDeckMutateAsync }),
}))

vi.mock('@/hooks/useSettings', () => ({
  useMySettings: () => ({ data: { active_personal_deck_id: 'deck-1' } }),
  useUpdateMySettings: () => ({ mutateAsync: updateSettingsMutateAsync }),
}))

describe('PersonalDeckSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the active deck name in the trigger', () => {
    render(<PersonalDeckSelector />)
    expect(screen.getByText('Mono Red')).toBeInTheDocument()
  })

  it('lists decks sorted alphabetically, not creation order', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))

    const names = screen
      .getAllByRole('option')
      .map((option) => option.textContent?.replace('✕', '').trim())
    expect(names).toEqual(['Azorius Control', '✓ Mono Red', 'Zendikar Ramp'])
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

  it('asks for confirmation before archiving, without selecting the deck', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.click(screen.getByRole('button', { name: 'Archive Azorius Control' }))

    expect(archiveDeckMutateAsync).not.toHaveBeenCalled()
    expect(updateSettingsMutateAsync).not.toHaveBeenCalled()
    expect(screen.getByText('Archive "Azorius Control"?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Archive' }))

    expect(archiveDeckMutateAsync).toHaveBeenCalledWith('deck-2')
    expect(updateSettingsMutateAsync).not.toHaveBeenCalled()
  })

  it('cancels without archiving', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.click(screen.getByRole('button', { name: 'Archive Azorius Control' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(archiveDeckMutateAsync).not.toHaveBeenCalled()
    expect(screen.queryByText('Archive "Azorius Control"?')).not.toBeInTheDocument()
  })

  it('clears the active deck when archiving it', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.click(screen.getByRole('button', { name: 'Archive Mono Red' }))
    await user.click(screen.getByRole('button', { name: 'Archive' }))

    expect(archiveDeckMutateAsync).toHaveBeenCalledWith('deck-1')
    expect(updateSettingsMutateAsync).toHaveBeenCalledWith({
      active_personal_deck_id: null,
    })
  })
})
