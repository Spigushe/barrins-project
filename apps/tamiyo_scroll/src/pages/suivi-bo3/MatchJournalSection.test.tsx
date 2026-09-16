import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Match, MatchGameEvent } from '@/schemas/tamiyoScroll'
import { MatchJournalSection } from './MatchJournalSection'

let nextEventId = 0
function event(comment: string | null = null): MatchGameEvent {
  nextEventId += 1
  return { id: `event-${String(nextEventId)}`, comment }
}

function game(
  gameNumber: number,
  result: 'win' | 'loss' | 'draw' | null,
  overrides: Partial<Match['games'][number]> = {},
): Match['games'][number] {
  return {
    game_number: gameNumber,
    on_play: true,
    result,
    player_mulligans: null,
    opponent_mulligans: null,
    player_misplays: null,
    opponent_misplays: null,
    ...overrides,
  }
}

const baseMatch: Match = {
  id: 'match-1',
  date: '2026-07-15',
  personal_deck_id: 'deck-mine',
  opponent_deck_id: 'deck-theirs',
  decklist_version_id: null,
  session_id: null,
  games: [game(1, 'win'), game(2, 'loss'), game(3, 'win')],
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

const deleteMatchMutateAsync = vi.fn()

vi.mock('@/hooks/useMatches', () => ({
  useMatches: () => ({ data: matches }),
  useUpdateMatch: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteMatch: () => ({ mutateAsync: deleteMatchMutateAsync, isPending: false }),
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
  closed_at: string | null
  archived_at: string | null
  hue: number | null
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
    matches = [{ ...baseMatch, games: [game(1, 'loss'), game(2, 'draw')] }]
    render(<MatchJournalSection />)
    expect(screen.getByText('Loss')).toBeInTheDocument()
  })

  it('still shows Draw once all three games are played with no majority', () => {
    matches = [{ ...baseMatch, games: [game(1, 'loss'), game(2, 'win'), game(3, 'draw')] }]
    render(<MatchJournalSection />)
    expect(screen.getByText('Draw')).toBeInTheDocument()
  })

  it('shows Win once a majority of games are won', () => {
    matches = [{ ...baseMatch, games: [game(1, 'win'), game(2, 'win')] }]
    render(<MatchJournalSection />)
    expect(screen.getByText('Win')).toBeInTheDocument()
  })

  it('shows no outcome badge for a match with no games entered yet (partial entry)', () => {
    matches = [{ ...baseMatch, games: [] }]
    render(<MatchJournalSection />)
    expect(screen.queryByText('Win')).not.toBeInTheDocument()
    expect(screen.queryByText('Loss')).not.toBeInTheDocument()
    expect(screen.queryByText('Draw')).not.toBeInTheDocument()
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

describe('MatchJournalSection — structured per-game data (#123/#124)', () => {
  beforeEach(() => {
    sessions = []
  })

  it('renders recorded mulligan/misplay events with their own comments in the View dialog', async () => {
    matches = [
      {
        ...baseMatch,
        games: [
          game(1, 'win', {
            player_mulligans: [event('Kept a risky one-lander')],
            player_misplays: [],
            opponent_mulligans: [],
            opponent_misplays: [event('Missed a combat trick'), event('Overextended')],
          }),
        ],
      },
    ]
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'View' }))

    const dialog = screen.getByRole('dialog')
    expect(dialog.textContent).toContain('Player — 1 mulligan(s), 0 misplay(s)')
    expect(dialog.textContent).toContain('Kept a risky one-lander')
    expect(dialog.textContent).toContain('Opponent — 0 mulligan(s), 2 misplay(s)')
    expect(dialog.textContent).toContain('Misplay #1: Missed a combat trick')
    expect(dialog.textContent).toContain('Misplay #2: Overextended')
  })

  it('renders no per-side detail line for a game with no gated data recorded', async () => {
    matches = [{ ...baseMatch, games: [game(1, 'win')] }]
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'View' }))

    const dialog = screen.getByRole('dialog')
    expect(dialog.textContent).not.toContain('Player —')
    expect(dialog.textContent).not.toContain('Opponent —')
  })

  it('renders a match with only some games entered (partial entry — game 1 live, no result yet)', async () => {
    matches = [{ ...baseMatch, games: [game(1, null)] }]
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    expect(screen.getByText('— / — / —')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'View' }))
    const dialog = screen.getByRole('dialog')
    expect(dialog.textContent).toContain('In progress')
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
      {
        id: 'session-1',
        name: 'RC Toronto 2026',
        type: 'tournament',
        closed_at: null,
        archived_at: null,
        hue: null,
      },
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

  it('tints the badge by hue instead of the type variant once a hue is set', () => {
    sessions = [{ ...sessions[0], hue: 200 }]
    render(<MatchJournalSection />)
    const badge = screen.getByText('Tournament: RC Toronto 2026')
    expect(badge).toHaveStyle({ backgroundColor: 'hsl(200 70% 50% / 0.18)' })
  })

  it('still resolves the tag for a match pointing at an archived session', () => {
    matches = [{ ...baseMatch, session_id: 'session-archived' }]
    sessions = [
      {
        id: 'session-archived',
        name: 'Old Regional',
        type: 'training',
        closed_at: '2026-07-01T00:00:00Z',
        archived_at: '2026-07-02T00:00:00Z',
        hue: null,
      },
    ]
    render(<MatchJournalSection />)
    expect(screen.getByText('Training: Old Regional')).toBeInTheDocument()
  })
})

describe('MatchJournalSection — delete confirmation', () => {
  beforeEach(() => {
    matches = [baseMatch]
    sessions = []
    deleteMatchMutateAsync.mockClear()
  })

  it('asks for confirmation before deleting, without deleting immediately', async () => {
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(deleteMatchMutateAsync).not.toHaveBeenCalled()
    expect(screen.getByText('Delete Mono Red vs Boros Energy?')).toBeInTheDocument()
  })

  it('deletes the match once confirmed', async () => {
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'Delete' }))
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }),
    )

    expect(deleteMatchMutateAsync).toHaveBeenCalledWith('match-1')
  })

  it('cancels without deleting', async () => {
    const user = userEvent.setup()
    render(<MatchJournalSection />)

    await user.click(screen.getByRole('button', { name: 'Delete' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(deleteMatchMutateAsync).not.toHaveBeenCalled()
    expect(screen.queryByText('Delete Mono Red vs Boros Energy?')).not.toBeInTheDocument()
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
