import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SessionsOverviewSection } from './SessionsSections'

interface MockSession {
  id: string
  owner_id: string
  personal_deck_id: string
  name: string
  type: 'tournament' | 'training'
  notes: string | null
  created_at: string
  ended_at: string | null
  archived_at: string | null
}

let canEdit = true
let sessions: MockSession[] = []
let comparisonBySessionId: Record<string, unknown> = {}

const createSessionMutateAsync = vi.fn()
const updateSessionMutateAsync = vi.fn()
const archiveSessionMutateAsync = vi.fn()
const downloadReportMutate = vi.fn()

vi.mock('@/contexts/active-deck-context', () => ({
  useActiveDeck: () => ({ activeDeckId: 'deck-mine', canEdit }),
}))

vi.mock('@/hooks/usePersonalDecks', () => ({
  usePersonalDecks: () => ({ data: [{ id: 'deck-mine', name: 'Mono Red' }] }),
}))

vi.mock('@/hooks/useMetaDecks', () => ({
  useMetaDecks: () => ({ data: [] }),
  useUpdateMetaDeck: () => ({ mutateAsync: vi.fn() }),
}))

vi.mock('@/hooks/useSessions', () => ({
  useSessions: () => ({ data: sessions }),
  useSessionComparison: (sessionId: string | null) => ({
    data: sessionId ? comparisonBySessionId[sessionId] : undefined,
  }),
  useCreateSession: () => ({
    mutateAsync: createSessionMutateAsync,
    isPending: false,
  }),
  useUpdateSession: () => ({ mutateAsync: updateSessionMutateAsync }),
  useArchiveSession: () => ({ mutateAsync: archiveSessionMutateAsync }),
  useDownloadSessionReport: () => ({
    mutate: downloadReportMutate,
    isPending: false,
  }),
}))

function matchupRow(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    opponent_deck_id: 'meta-1',
    opponent_deck_name: 'Boros Energy',
    winrate_global: 60,
    winrate_otp: 70,
    winrate_otd: 50,
    ratio_otp: '2-1',
    ratio_otd: '1-1',
    match_count: 3,
    is_readonly: false,
    has_shared_data: false,
    ...overrides,
  }
}

function comparisonFor(
  session: MockSession,
  overrides: Partial<Record<string, unknown>> = {},
) {
  return {
    session,
    session_match_count: 3,
    baseline_match_count: 10,
    session_wins: 2,
    session_losses: 1,
    baseline_wins: 5,
    baseline_losses: 5,
    session_archetype_summary: [],
    baseline_archetype_summary: [],
    session_matchup_summary: { rows: [], average_winrate: 66.67 },
    baseline_matchup_summary: { rows: [], average_winrate: 50 },
    ...overrides,
  }
}

const activeTrainingSession: MockSession = {
  id: 'session-active',
  owner_id: 'owner-1',
  personal_deck_id: 'deck-mine',
  name: 'Weekly Training',
  type: 'training',
  notes: null,
  created_at: '2026-07-01T00:00:00+00:00',
  ended_at: null,
  archived_at: null,
}

const closedTournamentSession: MockSession = {
  id: 'session-closed',
  owner_id: 'owner-1',
  personal_deck_id: 'deck-mine',
  name: 'RC Toronto 2026',
  type: 'tournament',
  notes: null,
  created_at: '2026-07-01T00:00:00+00:00',
  ended_at: '2026-07-02T00:00:00+00:00',
  archived_at: null,
}

beforeEach(() => {
  canEdit = true
  sessions = []
  comparisonBySessionId = {}
  createSessionMutateAsync.mockReset()
  updateSessionMutateAsync.mockReset()
  archiveSessionMutateAsync.mockReset()
  downloadReportMutate.mockReset()
})

describe('SessionsOverviewSection — merged sessions list', () => {
  it('lists ongoing and closed sessions together with a status badge each', () => {
    sessions = [activeTrainingSession, closedTournamentSession]
    render(<SessionsOverviewSection />)

    expect(screen.getByText('Sessions')).toBeInTheDocument()
    expect(screen.getByText('Weekly Training')).toBeInTheDocument()
    expect(screen.getByText('Ongoing')).toBeInTheDocument()
    expect(screen.getByText('RC Toronto 2026')).toBeInTheDocument()
    expect(screen.getByText('Closed')).toBeInTheDocument()
  })

  it('shows Close for an ongoing row and Reopen for a closed row', () => {
    sessions = [activeTrainingSession, closedTournamentSession]
    render(<SessionsOverviewSection />)

    expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reopen' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: '✕' })).toHaveLength(2)
  })

  it('hides the creation form and row actions in read-only mode, keeps the list', () => {
    canEdit = false
    sessions = [activeTrainingSession]
    render(<SessionsOverviewSection />)

    expect(screen.queryByPlaceholderText('e.g. RC Toronto 2026')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '✕' })).not.toBeInTheDocument()
    expect(screen.getByText('Weekly Training')).toBeInTheDocument()
  })

  it('creates a session for the active deck', async () => {
    createSessionMutateAsync.mockResolvedValue(activeTrainingSession)
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.type(
      screen.getByPlaceholderText('e.g. RC Toronto 2026'),
      'Weekly Training',
    )
    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(createSessionMutateAsync).toHaveBeenCalledWith({
      name: 'Weekly Training',
      type: 'training',
      personal_deck_id: 'deck-mine',
    })
  })

  it('closes an ongoing session', async () => {
    sessions = [activeTrainingSession]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: 'Close' }))

    expect(updateSessionMutateAsync).toHaveBeenCalledWith({
      sessionId: 'session-active',
      payload: { close: true },
    })
  })

  it('reopens a closed session', async () => {
    sessions = [closedTournamentSession]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: 'Reopen' }))

    expect(updateSessionMutateAsync).toHaveBeenCalledWith({
      sessionId: 'session-closed',
      payload: { reopen: true },
    })
  })

  it('asks for confirmation before archiving a session', async () => {
    sessions = [activeTrainingSession]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: '✕' }))

    expect(archiveSessionMutateAsync).not.toHaveBeenCalled()
    expect(screen.getByText('Archive "Weekly Training"?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Archive' }))

    expect(archiveSessionMutateAsync).toHaveBeenCalledWith('session-active')
  })

  it('cancels without archiving', async () => {
    sessions = [activeTrainingSession]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: '✕' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(archiveSessionMutateAsync).not.toHaveBeenCalled()
    expect(screen.queryByText('Archive "Weekly Training"?')).not.toBeInTheDocument()
  })

  it('excludes archived sessions from the list', () => {
    sessions = [{ ...activeTrainingSession, archived_at: '2026-07-05T00:00:00+00:00' }]
    render(<SessionsOverviewSection />)

    expect(screen.getByText('No session yet.')).toBeInTheDocument()
  })

  it('downloads a session report from its row icon', async () => {
    sessions = [activeTrainingSession]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: 'Download report (PDF)' }))

    expect(downloadReportMutate).toHaveBeenCalledWith({
      sessionId: 'session-active',
      filename: 'session-report-weekly-training.pdf',
    })
  })

  it('hides the report download icon in read-only mode', () => {
    canEdit = false
    sessions = [activeTrainingSession]
    render(<SessionsOverviewSection />)

    expect(
      screen.queryByRole('button', { name: 'Download report (PDF)' }),
    ).not.toBeInTheDocument()
  })
})

describe('SessionsOverviewSection — summary', () => {
  it('shows "select a session" until one is chosen', () => {
    render(<SessionsOverviewSection />)
    expect(
      screen.getByText('Select a session above to show its summary.'),
    ).toBeInTheDocument()
  })

  it('selecting a session shows its comparison summary', async () => {
    sessions = [closedTournamentSession]
    comparisonBySessionId = {
      'session-closed': comparisonFor(closedTournamentSession),
    }
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByText('RC Toronto 2026'))

    expect(screen.getByText('3')).toBeInTheDocument() // session_match_count
    expect(
      screen.getByText(/session 2W \/ 1L.*before the session 5W \/ 5L/),
    ).toBeInTheDocument()
  })

  it('shows Expected metagame only for a tournament-typed session', async () => {
    sessions = [activeTrainingSession, closedTournamentSession]
    comparisonBySessionId = {
      'session-active': comparisonFor(activeTrainingSession),
      'session-closed': comparisonFor(closedTournamentSession),
    }
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByText('Weekly Training'))
    expect(screen.queryByText('Expected metagame')).not.toBeInTheDocument()

    await user.click(screen.getByText('RC Toronto 2026'))
    expect(screen.getByText('Expected metagame')).toBeInTheDocument()
  })

  it('shows a per-opponent matchup comparison table with computed deltas', async () => {
    sessions = [closedTournamentSession]
    comparisonBySessionId = {
      'session-closed': comparisonFor(closedTournamentSession, {
        session_matchup_summary: {
          rows: [matchupRow({ winrate_global: 60, winrate_otp: 70, winrate_otd: 50 })],
          average_winrate: 60,
        },
        baseline_matchup_summary: {
          rows: [matchupRow({ winrate_global: 40, winrate_otp: 45, winrate_otd: 35 })],
          average_winrate: 40,
        },
      }),
    }
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByText('RC Toronto 2026'))

    expect(screen.getByText('Matchup comparison')).toBeInTheDocument()
    const row = screen.getByText('Boros Energy').closest('tr')
    if (!row) throw new Error('matchup row not found')
    const cells = within(row)
    expect(cells.getByText('40%')).toBeInTheDocument() // W/R global (baseline)
    expect(cells.getByText('60%')).toBeInTheDocument() // W/R session
    expect(cells.getByText('+20 pts')).toBeInTheDocument() // delta
    expect(cells.getByText('+25 pts')).toBeInTheDocument() // delta OTP (70-45)
    expect(cells.getByText('+15 pts')).toBeInTheDocument() // delta OTD (50-35)
  })

  it('omits the matchup comparison table when the session has no matches', async () => {
    sessions = [closedTournamentSession]
    comparisonBySessionId = {
      'session-closed': comparisonFor(closedTournamentSession),
    }
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByText('RC Toronto 2026'))

    expect(screen.queryByText('Matchup comparison')).not.toBeInTheDocument()
  })

  it('downloads the selected session report from the summary button', async () => {
    sessions = [closedTournamentSession]
    comparisonBySessionId = {
      'session-closed': comparisonFor(closedTournamentSession),
    }
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByText('RC Toronto 2026'))
    // Scoped to the summary card — the row above has its own PDF icon
    // button sharing the same accessible name.
    const summaryHeading = screen.getByRole('heading', { name: 'RC Toronto 2026' })
    const summaryCard = summaryHeading.closest('div')
    if (!summaryCard) throw new Error('summary card not found')
    await user.click(
      within(summaryCard).getByRole('button', { name: 'Download report (PDF)' }),
    )

    expect(downloadReportMutate).toHaveBeenCalledWith({
      sessionId: 'session-closed',
      filename: 'session-report-rc-toronto-2026.pdf',
    })
  })
})
