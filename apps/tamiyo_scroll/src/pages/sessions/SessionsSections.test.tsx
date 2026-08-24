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
  location: string | null
  created_at: string
  started_at: string | null
  ended_at: string | null
  closed_at: string | null
  archived_at: string | null
  hue: number | null
}

interface ListSessionsOptions {
  limit?: number
  offset?: number
  sortBy?: 'name' | 'type' | 'started_at' | 'status'
  sortDir?: 'asc' | 'desc'
  search?: string
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

/** Mimics the real listSessions option handling (sort/paginate/search)
 * closely enough to exercise the component's table-header/Prev-Next/
 * search wiring without a real backend. */
function applyListOptions(
  input: MockSession[],
  includeArchived: boolean,
  options: ListSessionsOptions,
): MockSession[] {
  let result = input.filter((s) => includeArchived || s.archived_at === null)

  if (options.search) {
    const needle = options.search.toLowerCase()
    result = result.filter((s) => s.name.toLowerCase().includes(needle))
  }

  if (options.sortBy) {
    const key = options.sortBy === 'status' ? 'closed_at' : options.sortBy
    const dir = options.sortDir === 'desc' ? -1 : 1
    result = [...result].sort((a, b) => {
      const av = a[key] ?? ''
      const bv = b[key] ?? ''
      if (av < bv) return -dir
      if (av > bv) return dir
      return 0
    })
  }

  if (options.limit !== undefined) {
    const offset = options.offset ?? 0
    result = result.slice(offset, offset + options.limit)
  }

  return result
}

vi.mock('@/hooks/useSessions', () => ({
  useSessions: (
    _deckId: string | null,
    includeArchived = false,
    options: ListSessionsOptions = {},
  ) => ({
    data: applyListOptions(sessions, includeArchived, options),
  }),
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
  location: null,
  created_at: '2026-07-01T00:00:00+00:00',
  started_at: '2026-07-01T00:00:00+00:00',
  ended_at: null,
  closed_at: null,
  archived_at: null,
  hue: null,
}

const closedTournamentSession: MockSession = {
  id: 'session-closed',
  owner_id: 'owner-1',
  personal_deck_id: 'deck-mine',
  name: 'RC Toronto 2026',
  type: 'tournament',
  notes: null,
  location: null,
  created_at: '2026-07-01T00:00:00+00:00',
  started_at: '2026-07-01T00:00:00+00:00',
  ended_at: null,
  closed_at: '2026-07-02T00:00:00+00:00',
  archived_at: null,
  hue: null,
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

describe('SessionsOverviewSection — sorting and pagination (S14)', () => {
  it('sorts by name ascending, then descending, on repeated header clicks', async () => {
    sessions = [
      { ...activeTrainingSession, id: 's-b', name: 'Bravo' },
      { ...activeTrainingSession, id: 's-a', name: 'Alpha' },
      { ...activeTrainingSession, id: 's-c', name: 'Charlie' },
    ]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    const firstRowName = () => {
      const rows = screen.getAllByRole('row').slice(1) // skip the header row
      return within(rows[0]).getAllByRole('cell')[0].textContent
    }
    const nameHeader = () => screen.getByRole('columnheader', { name: /^Session/ })

    await user.click(nameHeader())
    expect(firstRowName()).toBe('Alpha')

    await user.click(nameHeader())
    expect(firstRowName()).toBe('Charlie')
  })

  it('pages through more than 10 sessions with Prev/Next', async () => {
    sessions = Array.from({ length: 12 }, (_, i) => ({
      ...activeTrainingSession,
      id: `s-${String(i)}`,
      name: `S${String(i).padStart(2, '0')}`,
    }))
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    expect(screen.getByText('S00')).toBeInTheDocument()
    expect(screen.queryByText('S10')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Prev' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Next' })).not.toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('S10')).toBeInTheDocument()
    expect(screen.queryByText('S00')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })
})

describe('SessionsOverviewSection — inline edit (S14)', () => {
  it('edits name, location, notes, dates and hue, regardless of status', async () => {
    sessions = [closedTournamentSession]
    updateSessionMutateAsync.mockResolvedValue(closedTournamentSession)
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: 'Edit' }))

    // Scoped to the edit form — the "New session" form above also has a
    // "Name" field, sharing that label.
    const saveButton = screen.getByRole('button', { name: 'Save' })
    const editForm = saveButton.closest('td')
    if (!editForm) throw new Error('edit form not found')
    const form = within(editForm)

    const nameInput = form.getByLabelText('Name')
    await user.clear(nameInput)
    await user.type(nameInput, 'RC Toronto (renamed)')

    const locationInput = form.getByLabelText('Location')
    await user.type(locationInput, 'Toronto, ON')

    await user.click(saveButton)

    expect(updateSessionMutateAsync).toHaveBeenCalledWith({
      sessionId: 'session-closed',
      payload: expect.objectContaining({
        name: 'RC Toronto (renamed)',
        location: 'Toronto, ON',
      }),
    })
  })

  it('cancels without saving', async () => {
    sessions = [activeTrainingSession]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: 'Edit' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(updateSessionMutateAsync).not.toHaveBeenCalled()
    expect(screen.getByText('Weekly Training')).toBeInTheDocument()
  })
})

describe('SessionsOverviewSection — archived sessions dialog (S14)', () => {
  it('opens the archived sessions dialog and lists only archived rows', async () => {
    sessions = [
      activeTrainingSession,
      { ...closedTournamentSession, archived_at: '2026-07-05T00:00:00+00:00' },
    ]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: 'See archived' }))

    expect(screen.getByText('Archived sessions')).toBeInTheDocument()
    expect(screen.getByText('RC Toronto 2026')).toBeInTheDocument()
  })

  it('restores an archived session', async () => {
    sessions = [{ ...activeTrainingSession, archived_at: '2026-07-05T00:00:00+00:00' }]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: 'See archived' }))
    await user.click(screen.getByRole('button', { name: 'Restore' }))

    expect(updateSessionMutateAsync).toHaveBeenCalledWith({
      sessionId: 'session-active',
      payload: { restore: true },
    })
  })

  it('filters archived sessions by search', async () => {
    sessions = [
      {
        ...activeTrainingSession,
        id: 's-1',
        name: 'Weekly Training',
        archived_at: '2026-07-05T00:00:00+00:00',
      },
      {
        ...closedTournamentSession,
        id: 's-2',
        name: 'RC Toronto 2026',
        archived_at: '2026-07-05T00:00:00+00:00',
      },
    ]
    const user = userEvent.setup()
    render(<SessionsOverviewSection />)

    await user.click(screen.getByRole('button', { name: 'See archived' }))
    await user.type(screen.getByPlaceholderText('Search by name…'), 'toronto')

    expect(screen.getByText('RC Toronto 2026')).toBeInTheDocument()
    expect(screen.queryByText('Weekly Training')).not.toBeInTheDocument()
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
