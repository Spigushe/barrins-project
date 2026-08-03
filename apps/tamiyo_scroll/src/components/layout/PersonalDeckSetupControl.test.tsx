import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { PersonalDeck } from '@/schemas/tamiyoScroll'
import {
  personalDeckNeedsSetup,
  PersonalDeckSetupControl,
} from './PersonalDeckSetupControl'

const updateDeckMutateAsync = vi.fn()

vi.mock('@/hooks/usePersonalDecks', () => ({
  useUpdatePersonalDeck: () => ({ mutateAsync: updateDeckMutateAsync, isPending: false }),
}))

const fullDeck: PersonalDeck = {
  id: 'deck-1',
  name: 'Mono Red',
  game: 'magic',
  category: 'aggro',
  archived_at: null,
  created_at: '',
}

describe('personalDeckNeedsSetup', () => {
  it('is false for a fully set-up deck', () => {
    expect(personalDeckNeedsSetup(fullDeck)).toBe(false)
  })

  it('is true when game is missing', () => {
    expect(personalDeckNeedsSetup({ ...fullDeck, game: null })).toBe(true)
  })

  it('is true when category is missing', () => {
    expect(personalDeckNeedsSetup({ ...fullDeck, category: null })).toBe(true)
  })

  it('is false for undefined/null (no deck selected yet)', () => {
    expect(personalDeckNeedsSetup(undefined)).toBe(false)
    expect(personalDeckNeedsSetup(null)).toBe(false)
  })
})

describe('PersonalDeckSetupControl', () => {
  it('renders nothing for a fully set-up deck', () => {
    const { container } = render(<PersonalDeckSetupControl deck={fullDeck} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('saves the chosen game and category for a deck missing both', async () => {
    const user = userEvent.setup()
    render(
      <PersonalDeckSetupControl deck={{ ...fullDeck, game: null, category: null }} />,
    )

    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()

    const [gameTrigger, archetypeTrigger] = screen
      .getAllByRole('combobox')
      .filter((el) => el.tagName === 'BUTTON')
    await user.click(gameTrigger)
    await user.click(screen.getByText('Yu-Gi-Oh!'))
    await user.click(archetypeTrigger)
    await user.click(screen.getByText('Control'))

    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(updateDeckMutateAsync).toHaveBeenCalledWith({
      deckId: 'deck-1',
      game: 'yu_gi_oh',
      category: 'control',
    })
  }, 15000)
})
