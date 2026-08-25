import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { Table, TableBody } from '@/components/ui/table'
import type { DecklistCard } from '@/schemas/tamiyoScroll'
import { DecklistCardRow } from './DecklistCardRow'

function renderRow(card: DecklistCard) {
  return render(
    <Table>
      <TableBody>
        <DecklistCardRow card={card} />
      </TableBody>
    </Table>,
  )
}

const baseCard: DecklistCard = {
  qty: 2,
  name: 'Duress',
  status: 'neutral',
  mana_cost: '{B}',
  type_line: 'Sorcery',
  text: 'Target opponent reveals their hand.',
  keywords: [],
  scryfall_id: 'duress-scryfall-id',
}

describe('DecklistCardRow — S17 pending inline display', () => {
  it('renders a plain non-pending line unchanged', () => {
    renderRow(baseCard)

    expect(screen.getByText('Duress')).toBeInTheDocument()
    expect(screen.queryByText('→')).not.toBeInTheDocument()
  })

  it('renders the removed name struck through, an arrow, and the added name when pending', () => {
    renderRow({
      ...baseCard,
      status: 'pending',
      pending_added_card_name: 'Thoughtseize',
      pending_added_card_scryfall_id: 'thoughtseize-scryfall-id',
    })

    const removed = screen.getByText('Duress')
    expect(removed).toHaveClass('line-through')
    expect(screen.getByText('→')).toBeInTheDocument()
    expect(screen.getByText('Thoughtseize')).toBeInTheDocument()
  })

  it('shows the added card image on hover over the added name, not the removed card', async () => {
    const user = userEvent.setup()
    renderRow({
      ...baseCard,
      status: 'pending',
      pending_added_card_name: 'Thoughtseize',
      pending_added_card_scryfall_id: 'thoughtseize-scryfall-id',
    })

    await user.hover(screen.getByText('Thoughtseize'))
    expect(await screen.findByAltText('Thoughtseize')).toBeInTheDocument()
  })

  it('feeds the pips and info popover from the added card while pending', async () => {
    const user = userEvent.setup()
    renderRow({
      ...baseCard,
      status: 'pending',
      mana_cost: '{B}',
      keywords: ['Removed-card-keyword'],
      text: 'Removed card oracle text.',
      pending_added_card_name: 'Thoughtseize',
      pending_added_card_scryfall_id: 'thoughtseize-scryfall-id',
      pending_added_card_mana_cost: '{B}{B}',
      pending_added_card_text: 'Added card oracle text.',
      pending_added_card_keywords: ['Added-card-keyword'],
    })

    // pips: two "B" tokens (from the added card's {B}{B}), not one.
    expect(screen.getAllByText('B')).toHaveLength(2)

    await user.click(screen.getByRole('button', { name: 'Duress info' }))
    expect(await screen.findByText('Added card oracle text.')).toBeInTheDocument()
    expect(screen.getByText('Added-card-keyword')).toBeInTheDocument()
    expect(screen.queryByText('Removed card oracle text.')).not.toBeInTheDocument()
    expect(screen.queryByText('Removed-card-keyword')).not.toBeInTheDocument()
  })

  it('falls back to no pips/popover data when the added card does not resolve', async () => {
    const user = userEvent.setup()
    renderRow({
      ...baseCard,
      status: 'pending',
      mana_cost: '{B}',
      pending_added_card_name: 'Not A Real Card',
      pending_added_card_scryfall_id: null,
      pending_added_card_mana_cost: null,
      pending_added_card_text: null,
      pending_added_card_keywords: [],
    })

    expect(screen.queryByText('B')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Duress info' }))
    expect(await screen.findByText('No oracle text.')).toBeInTheDocument()
  })
})
