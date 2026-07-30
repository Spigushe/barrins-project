import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Match } from '@/schemas/tamiyoScroll'
import { MatchJournalSection } from './MatchJournalSection'

const baseMatch: Match = {
  id: 'match-1',
  date: '2026-07-15',
  personal_deck_id: 'deck-mine',
  opponent_deck_id: 'deck-theirs',
  decklist_version_id: null,
  on_play: true,
  game1: 'win',
  game2: 'loss',
  game3: 'win',
  opening_hand: 'Two lands, Bolt, Ponder',
  turning_point: 'Resolved a Cryptic Command on turn 4',
  final_turn: 'Attacked for lethal turn 8',
  created_at: '2026-07-15T12:00:00+00:00',
  is_readonly: false,
  shared_by: null,
}

const sharedMatch: Match = {
  ...baseMatch,
  id: 'match-2',
  is_readonly: true,
  shared_by: 'other@example.com',
}

let matches: Match[] = [baseMatch]

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-mine', canEdit: true }),
}))

vi.mock('@/hooks/useMatches', () => ({
  useMatches: () => ({ data: matches }),
  useUpdateMatch: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteMatch: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/useMetaDecks', () => ({
  useMetaDecks: () => ({ data: [{ id: 'deck-theirs', name: 'Boros Energy' }] }),
}))

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({ data: [{ id: 'deck-mine', name: 'Mono Red' }] }),
}))

vi.mock('@/hooks/useDecklistVersions', () => ({
  useDecklistVersions: () => ({ data: [] }),
}))

describe('MatchJournalSection — View button', () => {
  beforeEach(() => {
    matches = [baseMatch]
  })

  it('does not show match notes in the collapsed row', () => {
    render(<MatchJournalSection />)
    expect(screen.queryByText(/Two lands, Bolt/)).not.toBeInTheDocument()
  })

  it('opens a read-only dialog with the match notes when View is clicked', async () => {
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'View' }))

    expect(screen.getByText('Two lands, Bolt, Ponder')).toBeInTheDocument()
    expect(screen.getByText('Resolved a Cryptic Command on turn 4')).toBeInTheDocument()
    expect(screen.getByText('Attacked for lethal turn 8')).toBeInTheDocument()
  })

  it('places View before Edit and Delete', () => {
    render(<MatchJournalSection />)
    const buttons = screen.getAllByRole('button').map((button) => button.textContent)
    expect(buttons.indexOf('View')).toBeLessThan(buttons.indexOf('Edit'))
    expect(buttons.indexOf('Edit')).toBeLessThan(buttons.indexOf('Delete'))
  })
})

describe('MatchJournalSection — shared (read-only) matches', () => {
  beforeEach(() => {
    matches = [sharedMatch]
  })

  it('hides both Edit and Delete for a shared match', () => {
    render(<MatchJournalSection />)
    expect(screen.getByRole('button', { name: 'View' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
  })

  it('shows a "from: {sharer}" badge on the collapsed row', () => {
    render(<MatchJournalSection />)
    expect(screen.getByText('from: other@example.com')).toBeInTheDocument()
  })

  it('shows a "from: {sharer}" badge in the View popup', async () => {
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'View' }))

    expect(screen.getAllByText('from: other@example.com')).toHaveLength(2)
  })
})
