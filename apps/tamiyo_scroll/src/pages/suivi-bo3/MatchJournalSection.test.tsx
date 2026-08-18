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
  session_id: null,
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

const activeMetaDecks: { id: string; name: string }[] = [
  { id: 'deck-theirs', name: 'Boros Energy' },
]
let archivedOnlyMetaDecks: { id: string; name: string }[] = []

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-mine', canEdit: true }),
}))

vi.mock('@/hooks/useMatches', () => ({
  useMatches: () => ({ data: matches }),
  useUpdateMatch: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteMatch: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/useMetaDecks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useMetaDecks')>()
  return {
    ...actual,
    useMetaDecks: (options?: { includeArchived?: boolean }) =>
      options?.includeArchived
        ? { data: [...activeMetaDecks, ...archivedOnlyMetaDecks] }
        : { data: activeMetaDecks },
  }
})

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({ data: [{ id: 'deck-mine', name: 'Mono Red' }] }),
}))

vi.mock('@/hooks/useDecklistVersions', () => ({
  useDecklistVersions: () => ({ data: [] }),
}))

let sessions: {
  id: string
  name: string
  type: 'tournament' | 'training'
  ended_at: string | null
}[] = []

vi.mock('@/hooks/useSessions', () => ({
  useSessions: () => ({ data: sessions }),
  useCreateSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

describe('MatchJournalSection — match outcome badge', () => {
  beforeEach(() => {
    sessions = []
  })

  it('shows Loss for a loss + draw with the third game not yet played', () => {
    matches = [{ ...baseMatch, game1: 'loss', game2: 'draw', game3: null }]
    render(<MatchJournalSection />)
    expect(screen.getByText('Loss')).toBeInTheDocument()
  })

  it('still shows Draw once all three games are played with no majority', () => {
    matches = [{ ...baseMatch, game1: 'loss', game2: 'win', game3: 'draw' }]
    render(<MatchJournalSection />)
    expect(screen.getByText('Draw')).toBeInTheDocument()
  })

  it('shows Win once a majority of games are won', () => {
    matches = [{ ...baseMatch, game1: 'win', game2: 'win', game3: null }]
    render(<MatchJournalSection />)
    expect(screen.getByText('Win')).toBeInTheDocument()
  })
})

describe('MatchJournalSection — View button', () => {
  beforeEach(() => {
    matches = [baseMatch]
    sessions = []
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
    sessions = []
  })

  it('hides both Edit and Delete for a shared match', () => {
    render(<MatchJournalSection />)
    expect(screen.getByRole('button', { name: 'View' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument()
  })

  it('shows a "sharer: {sharer}" badge on the collapsed row', () => {
    render(<MatchJournalSection />)
    expect(screen.getByText('sharer: other@example.com')).toBeInTheDocument()
  })

  it('shows a "sharer: {sharer}" badge in the View popup', async () => {
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'View' }))

    expect(screen.getAllByText('sharer: other@example.com')).toHaveLength(2)
  })
})

describe('MatchJournalSection — session badge', () => {
  beforeEach(() => {
    matches = [{ ...baseMatch, session_id: 'session-1' }]
    sessions = [
      { id: 'session-1', name: 'RC Toronto 2026', type: 'tournament', ended_at: null },
    ]
  })

  it('shows the session name, prefixed by its type and colored accordingly, on the collapsed row', () => {
    render(<MatchJournalSection />)
    const badge = screen.getByText('Tournament: RC Toronto 2026')
    expect(badge).toBeInTheDocument()
    // tournament -> tournament variant (see SESSION_TYPE_BADGE_VARIANT)
    expect(badge.className).toContain('text-tournament')
  })

  it('shows the session name in the View popup', async () => {
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'View' }))

    expect(screen.getAllByText('Tournament: RC Toronto 2026')).toHaveLength(2)
  })
})

describe('MatchJournalSection — opponent deck resolution', () => {
  beforeEach(() => {
    sessions = []
    archivedOnlyMetaDecks = []
  })

  it('shows "Deleted deck" when the opponent exists but is archived', () => {
    matches = [{ ...baseMatch, opponent_deck_id: 'deck-archived' }]
    archivedOnlyMetaDecks = [{ id: 'deck-archived', name: 'Old Boros Energy' }]
    render(<MatchJournalSection />)
    expect(screen.getByText('Deleted deck')).toBeInTheDocument()
  })

  it('falls back to "?" when the opponent cannot be resolved at all', () => {
    matches = [{ ...baseMatch, opponent_deck_id: 'deck-unknown' }]
    render(<MatchJournalSection />)
    expect(screen.getByText('?')).toBeInTheDocument()
  })
})
