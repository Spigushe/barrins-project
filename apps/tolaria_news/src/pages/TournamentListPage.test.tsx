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
    enabled: boolean | undefined,
  ): ReturnType<typeof useTournamentsMock> =>
    useTournamentsMock(filters, cursor, enabled),
}))

const trendMeta = { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null }

function trendsWithWindow(dateFrom: string, dateTo: string) {
  return {
    data: {
      window: {
        kind: 'banlist_period',
        label: `banlist_period:${dateFrom}_${dateTo}`,
        date_from: dateFrom,
        date_to: dateTo,
      },
      series: [] as unknown[],
    },
    meta: trendMeta,
    page: null,
  }
}

const currentSeasonTrends = trendsWithWindow('2026-07-02', '2026-08-01')

const tymnaTrends = {
  data: {
    window: currentSeasonTrends.data.window,
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
    dateFrom: unknown,
    dateTo: unknown,
  ): ReturnType<typeof useTrendingCommandersMock> =>
    useTrendingCommandersMock(mode, periodOffset, dateFrom, dateTo),
}))

const emptyStaples = {
  data: {
    date_from: '2026-07-02',
    date_to: '2026-08-01',
    tournaments_considered: 0,
    decks_considered: 0,
    min_percentage: 75,
    rows: [] as unknown[],
  },
  meta: trendMeta,
  page: null,
}

const solRingStaples = {
  data: {
    date_from: '2026-07-02',
    date_to: '2026-08-01',
    tournaments_considered: 3,
    decks_considered: 4,
    min_percentage: 75,
    rows: [
      {
        name: 'Sol Ring',
        cmc: 1,
        type_line: 'Artifact',
        scryfall_id: 'sol-ring-scryfall-id',
        mana_cost: '{1}',
        text: null,
        keywords: [],
        deck_count: 3,
        percentage: 75,
      },
    ],
  },
  meta: trendMeta,
  page: null,
}

const useStaplesMock = vi.fn()

vi.mock('@/hooks/useDecks', () => ({
  useStaples: (dateFrom: unknown, dateTo: unknown): ReturnType<typeof useStaplesMock> =>
    useStaplesMock(dateFrom, dateTo),
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
      data: currentSeasonTrends,
      isLoading: false,
      isError: false,
      error: null,
    })

    useStaplesMock.mockReset()
    useStaplesMock.mockReturnValue({
      data: emptyStaples,
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

  it('passes the resolved window as the date_from/date_to table filter', () => {
    renderPage()

    expect(useTournamentsMock).toHaveBeenCalledWith(
      expect.objectContaining({ dateFrom: '2026-07-02', dateTo: '2026-08-01' }),
      undefined,
      true,
    )
  })

  it('does not query the table until the window has resolved', () => {
    useTrendingCommandersMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    })
    renderPage()

    expect(useTournamentsMock).toHaveBeenCalledWith(expect.anything(), undefined, false)
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
  })

  describe('window filter', () => {
    it('defaults to the current banlist season', () => {
      renderPage()

      expect(useTrendingCommandersMock).toHaveBeenLastCalledWith(
        'banlist_period',
        0,
        undefined,
        undefined,
      )
    })

    it('switches to the previous banlist season', async () => {
      const user = userEvent.setup()
      renderPage()

      await user.selectOptions(screen.getByLabelText('Window'), 'previous_season')

      expect(useTrendingCommandersMock).toHaveBeenLastCalledWith(
        'banlist_period',
        1,
        undefined,
        undefined,
      )
    })

    it('switches to the 20-life decks preset with a fixed start date', async () => {
      const user = userEvent.setup()
      renderPage()

      await user.selectOptions(screen.getByLabelText('Window'), 'life_20')

      expect(useTrendingCommandersMock).toHaveBeenLastCalledWith(
        'custom',
        undefined,
        '2016-11-11',
        undefined,
      )
    })

    it('switches to all time', async () => {
      const user = userEvent.setup()
      renderPage()

      await user.selectOptions(screen.getByLabelText('Window'), 'all_time')

      expect(useTrendingCommandersMock).toHaveBeenLastCalledWith(
        'all_time',
        undefined,
        undefined,
        undefined,
      )
    })

    it('reveals date pickers for a custom range and passes the picked dates', async () => {
      const user = userEvent.setup()
      renderPage()

      await user.selectOptions(screen.getByLabelText('Window'), 'custom')
      await user.type(screen.getByLabelText('From'), '2026-01-01')
      await user.type(screen.getByLabelText('To'), '2026-02-01')

      expect(useTrendingCommandersMock).toHaveBeenLastCalledWith(
        'custom',
        undefined,
        '2026-01-01',
        '2026-02-01',
      )
    })

    it('does not show date pickers for non-custom presets', () => {
      renderPage()

      expect(screen.queryByLabelText('From')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('To')).not.toBeInTheDocument()
    })
  })

  describe('staples section', () => {
    it('shows an empty state message using the response min_percentage', () => {
      renderPage()

      expect(
        screen.getByText('No card is played in at least 75% of decks for this window.'),
      ).toBeInTheDocument()
    })

    it('renders staple rows with deck count and percentage', () => {
      useStaplesMock.mockReturnValue({
        data: solRingStaples,
        isLoading: false,
        isError: false,
        error: null,
      })
      renderPage()

      expect(screen.getByText('Sol Ring')).toBeInTheDocument()
      expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('passes the resolved window to useStaples', () => {
      renderPage()

      expect(useStaplesMock).toHaveBeenLastCalledWith('2026-07-02', '2026-08-01')
    })

    it('has nothing resolved to pass until the shared window resolves', () => {
      useTrendingCommandersMock.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      })
      renderPage()

      expect(useStaplesMock).toHaveBeenLastCalledWith(undefined, undefined)
    })
  })
})
