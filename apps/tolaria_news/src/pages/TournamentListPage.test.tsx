import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TournamentListPage } from './TournamentListPage'

const meta = { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null }

const page1 = {
  data: [
    {
      id: 't1',
      source: 'mtgo',
      date: '2026-08-01',
      name: 'Legacy League',
      url: 'https://x',
      format: 'Legacy',
      players: 32,
    },
  ],
  meta,
  page: { next_cursor: 'abc', limit: 20 },
}

const page2 = {
  data: [
    {
      id: 't2',
      source: 'mtgtop8',
      date: '2026-08-02',
      name: 'Duel Commander Open',
      url: 'https://y',
      format: 'Duel Commander',
      players: 16,
    },
  ],
  meta,
  page: { next_cursor: null, limit: 20 },
}

const useTournamentsMock = vi.fn()

vi.mock('@/hooks/useTournaments', () => ({
  useTournaments: (
    filters: unknown,
    cursor: string | undefined,
  ): ReturnType<typeof useTournamentsMock> => useTournamentsMock(filters, cursor),
}))

const trendMeta = { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null }

const emptyTrends = {
  data: {
    window: {
      kind: 'rolling_30d',
      label: 'rolling_30d:2026-08-01',
      date_from: '2026-07-02',
      date_to: '2026-08-01',
    },
    series: [],
  },
  meta: trendMeta,
  page: null,
}

const tymnaTrends = {
  data: {
    window: {
      kind: 'rolling_30d',
      label: 'rolling_30d:2026-08-01',
      date_from: '2026-07-02',
      date_to: '2026-08-01',
    },
    series: [
      {
        commanders: [
          {
            name: 'Tymna the Weaver',
            scryfall_id: 'tymna-scryfall-id',
            color_identity: ['W', 'B'],
            mana_cost: '{1}{W}{B}',
            text: null,
            keywords: [],
          },
        ],
        total_deck_count: 3,
        points: [
          { date_from: '2026-07-02', date_to: '2026-07-08', deck_count: null },
          { date_from: '2026-07-09', date_to: '2026-07-15', deck_count: 3 },
        ],
      },
    ],
  },
  meta: trendMeta,
  page: null,
}

const useTrendingCommandersMock = vi.fn()

vi.mock('@/hooks/useCommanderTrends', () => ({
  useTrendingCommanders: (
    mode: unknown,
    periodOffset: unknown,
  ): ReturnType<typeof useTrendingCommandersMock> =>
    useTrendingCommandersMock(mode, periodOffset),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <TournamentListPage />
    </MemoryRouter>,
  )
}

describe('TournamentListPage', () => {
  beforeEach(() => {
    useTournamentsMock.mockReset()
    useTournamentsMock.mockImplementation((_filters: unknown, cursor?: string) => ({
      data: cursor === 'abc' ? page2 : page1,
      isLoading: false,
      isError: false,
      error: null,
    }))

    useTrendingCommandersMock.mockReset()
    useTrendingCommandersMock.mockReturnValue({
      data: emptyTrends,
      isLoading: false,
      isError: false,
      error: null,
    })
  })

  it('renders tournament rows with a source badge and a link to detail', () => {
    renderPage()

    expect(screen.getByRole('link', { name: 'Legacy League' })).toHaveAttribute(
      'href',
      '/tournaments/t1',
    )
    expect(screen.getByText('mtgo')).toBeInTheDocument()
  })

  it('advances to the next page using the returned cursor', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Next' }))

    expect(screen.getByRole('link', { name: 'Duel Commander Open' })).toBeInTheDocument()
  })

  it('shows an empty state when no tournaments match the filters', () => {
    useTournamentsMock.mockReturnValue({
      data: { data: [], meta, page: null },
      isLoading: false,
      isError: false,
      error: null,
    })
    renderPage()

    expect(screen.getByText('No tournaments match these filters.')).toBeInTheDocument()
  })

  describe('commander trend chips', () => {
    it('shows an empty state when no decks are recorded in the window', () => {
      renderPage()

      expect(screen.getByText('No decks recorded in this window.')).toBeInTheDocument()
    })

    it('renders a chip with the commander name and total deck count', () => {
      useTrendingCommandersMock.mockReturnValue({
        data: tymnaTrends,
        isLoading: false,
        isError: false,
        error: null,
      })
      renderPage()

      expect(screen.getByText('Tymna the Weaver')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
    })

    it('switches window mode, resetting to the current period', async () => {
      const user = userEvent.setup()
      renderPage()

      await user.selectOptions(screen.getByLabelText('Window'), 'banlist_period')

      expect(useTrendingCommandersMock).toHaveBeenLastCalledWith('banlist_period', 0)
      expect(screen.getByRole('button', { name: '← Earlier period' })).toBeInTheDocument()
    })

    it('steps into an earlier banlist period', async () => {
      const user = userEvent.setup()
      renderPage()
      await user.selectOptions(screen.getByLabelText('Window'), 'banlist_period')

      await user.click(screen.getByRole('button', { name: '← Earlier period' }))

      expect(useTrendingCommandersMock).toHaveBeenLastCalledWith('banlist_period', 1)
    })
  })
})
