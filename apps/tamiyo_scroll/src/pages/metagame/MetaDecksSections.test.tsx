import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MetaDecksRosterSection } from './MetaDecksSections'

const decks = [
  { id: '1', name: 'Zenith Combo', tier: 1, category: 'combo', decklist_notes: null },
  { id: '2', name: 'Boros Aggro', tier: 0.5, category: 'aggro', decklist_notes: null },
  {
    id: '3',
    name: 'Azorius Control',
    tier: 1,
    category: 'control',
    decklist_notes: null,
  },
]

const activeDeckState = vi.hoisted(() => ({ canEdit: false }))

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ canEdit: activeDeckState.canEdit, activeDeckId: 'deck-1' }),
}))

const archiveDeckMutateAsync = vi.fn()

vi.mock('@/hooks/useMetaDecks', () => ({
  useMetaDecks: () => ({ data: decks }),
  useCreateMetaDeck: () => ({ mutateAsync: vi.fn() }),
  useUpdateMetaDeck: () => ({ mutateAsync: vi.fn() }),
  useArchiveMetaDeck: () => ({ mutateAsync: archiveDeckMutateAsync }),
}))

describe('MetaDecksRosterSection sorting', () => {
  it('sorts by tier ascending, then name ascending within the same tier', () => {
    render(<MetaDecksRosterSection />)

    const nameInputs = screen
      .getAllByRole('textbox')
      .filter((_, index) => index % 2 === 0) // name input is first of the 2 inputs per row

    expect(nameInputs.map((input) => (input as HTMLInputElement).value)).toEqual([
      'Boros Aggro', // tier 0.5
      'Azorius Control', // tier 1, name asc
      'Zenith Combo', // tier 1, name asc
    ])
  })
})

// S12 item 12: delete now requires confirmation via a Dialog (same pattern
// as PersonalDeckSelector's archive confirm), not a direct call.
describe('MetaDecksRosterSection — delete confirmation', () => {
  beforeEach(() => {
    activeDeckState.canEdit = true
    archiveDeckMutateAsync.mockClear()
  })

  afterEach(() => {
    activeDeckState.canEdit = false
  })

  it('asks for confirmation before deleting, without archiving immediately', async () => {
    const user = userEvent.setup()
    render(<MetaDecksRosterSection />)

    await user.click(screen.getAllByRole('button', { name: '✕' })[0])

    expect(archiveDeckMutateAsync).not.toHaveBeenCalled()
    expect(screen.getByText('Delete "Boros Aggro"?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(archiveDeckMutateAsync).toHaveBeenCalledWith('2')
  })

  it('cancels without deleting', async () => {
    const user = userEvent.setup()
    render(<MetaDecksRosterSection />)

    await user.click(screen.getAllByRole('button', { name: '✕' })[0])
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(archiveDeckMutateAsync).not.toHaveBeenCalled()
    expect(screen.queryByText('Delete "Boros Aggro"?')).not.toBeInTheDocument()
  })
})

// S12 items 10-11: opt-in, `localStorage`-backed roster display prefs.
describe('MetaDecksRosterSection — display prefs', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('leaves the archetype trigger uncolored by default', () => {
    render(<MetaDecksRosterSection />)
    const trigger = screen.getAllByRole('combobox')[1] // tier, archetype, ... per row
    expect(trigger.className).not.toContain('text-archetype')
  })

  it('colors the archetype trigger when the preference is enabled', () => {
    localStorage.setItem('ts-roster-archetype-color-enabled', 'true')
    render(<MetaDecksRosterSection />)
    const triggers = screen.getAllByRole('combobox')
    // Boros Aggro (index 0 row): tier trigger then archetype trigger.
    expect(triggers[1].className).toContain('text-archetype-aggro')
    expect(triggers[1].className).toContain('border-archetype-aggro')
  })

  it('leaves the tier cell unstyled by default', () => {
    render(<MetaDecksRosterSection />)
    const tierCell = screen.getAllByRole('combobox')[0].closest('td')
    expect(tierCell?.className ?? '').not.toContain('bg-')
  })

  it('colors the tier cell when the preference is enabled', () => {
    localStorage.setItem('ts-roster-tier-color-enabled', 'true')
    render(<MetaDecksRosterSection />)
    // First row is Boros Aggro, tier 0.5 → the "strong" (green) band.
    const tierCell = screen.getAllByRole('combobox')[0].closest('td')
    expect(tierCell?.className).toContain('bg-success/10')
  })
})
