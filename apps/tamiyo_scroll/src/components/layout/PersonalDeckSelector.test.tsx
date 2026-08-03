import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PersonalDeckSelector } from './PersonalDeckSelector'

const updateSettingsMutateAsync = vi.fn()
const createDeckMutateAsync = vi.fn()
const archiveDeckMutateAsync = vi.fn()
const updateDeckMutateAsync = vi.fn()

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({
    data: [
      {
        id: 'deck-1',
        name: 'Mono Red',
        game: 'magic',
        category: 'aggro',
        archived_at: null,
        created_at: '',
      },
      {
        id: 'deck-2',
        name: 'Azorius Control',
        game: 'magic',
        category: 'control',
        archived_at: null,
        created_at: '',
      },
      {
        id: 'deck-4',
        name: 'Zendikar Ramp',
        game: 'magic',
        category: 'midrange',
        archived_at: null,
        created_at: '',
      },
    ],
  }),
  useCreatePersonalDeck: () => ({ mutateAsync: createDeckMutateAsync }),
  useArchivePersonalDeck: () => ({ mutateAsync: archiveDeckMutateAsync }),
  useUpdatePersonalDeck: () => ({ mutateAsync: updateDeckMutateAsync, isPending: false }),
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
      .map((option) => option.textContent?.replace('✎', '').replace('✕', '').trim())
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

  it('creates and auto-selects a new deck once game and archetype are both set', { timeout: 15000 }, async () => {
    createDeckMutateAsync.mockResolvedValue({
      id: 'deck-3',
      name: 'Boros Aggro',
      game: 'magic',
      category: 'aggro',
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

    // Create is disabled until both required selects are set.
    expect(screen.getByRole('button', { name: 'Create' })).toBeDisabled()

    // cmdk's search input is also role="combobox" — narrow to the two
    // Select triggers (rendered as <button>, unlike the <input> search box).
    const [gameTrigger, archetypeTrigger] = screen
      .getAllByRole('combobox')
      .filter((el) => el.tagName === 'BUTTON')
    await user.click(gameTrigger)
    await user.click(screen.getByText('Magic: The Gathering'))
    await user.click(archetypeTrigger)
    await user.click(screen.getByText('Aggro'))

    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(createDeckMutateAsync).toHaveBeenCalledWith({
      name: 'Boros Aggro',
      game: 'magic',
      category: 'aggro',
    })
    expect(updateSettingsMutateAsync).toHaveBeenCalledWith({
      active_personal_deck_id: 'deck-3',
    })
  })

  it('does not offer to create a deck that already exists by that name', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.type(screen.getByPlaceholderText('Search or create a deck…'), 'Mono Red')

    expect(screen.queryByRole('button', { name: 'Create' })).not.toBeInTheDocument()
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

  it('renames a deck, pre-filled with its current name', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.click(screen.getByRole('button', { name: 'Rename Azorius Control' }))

    expect(screen.getByText('Rename "Azorius Control"')).toBeInTheDocument()
    const input = screen.getByLabelText('New deck name')
    expect(input).toHaveValue('Azorius Control')

    await user.clear(input)
    await user.type(input, 'Jeskai Control')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateDeckMutateAsync).toHaveBeenCalledWith({
      deckId: 'deck-2',
      name: 'Jeskai Control',
    })
  })

  it('cancels without renaming', async () => {
    const user = userEvent.setup()
    render(<PersonalDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'My personal deck' }))
    await user.click(screen.getByRole('button', { name: 'Rename Azorius Control' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(updateDeckMutateAsync).not.toHaveBeenCalled()
    expect(screen.queryByText('Rename "Azorius Control"')).not.toBeInTheDocument()
  })
})
