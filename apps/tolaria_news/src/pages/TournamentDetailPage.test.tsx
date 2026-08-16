import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TournamentDetailPage } from './TournamentDetailPage'
import {
  useTournament,
  useTournamentDecks,
  useTournamentStandings,
  useTournamentBracket,
} from '@/hooks/useTournaments'

vi.mock('@/hooks/useTournaments', () => ({
  useTournament: vi.fn(),
  useTournamentDecks: vi.fn(),
  useTournamentStandings: vi.fn(),
  useTournamentBracket: vi.fn(),
}))

const meta = { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null }

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/tournaments/t1']}>
      <Routes>
        <Route path="/tournaments/:id" element={<TournamentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TournamentDetailPage', () => {
  beforeEach(() => {
    vi.mocked(useTournament).mockReturnValue({
      data: {
        data: {
          id: 't1',
          source: 'mtgo',
          date: '2026-08-01',
          name: 'Legacy League',
          url: 'https://x',
          format: 'Legacy',
          players: 32,
          deck_count: 1,
          standing_count: 1,
        },
        meta,
        page: null,
      },
      isLoading: false,
      isError: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any)

    vi.mocked(useTournamentDecks).mockReturnValue({
      data: {
        data: [
          {
            id: 'd1',
            tournament_id: 't1',
            date: '2026-08-01',
            player: 'Alice',
            result: '3-1',
            anchor_uri: 'x',
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
          },
        ],
        meta,
        page: { next_cursor: null, limit: 20 },
      },
      isLoading: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any)

    vi.mocked(useTournamentStandings).mockReturnValue({
      data: {
        data: [
          {
            rank: 1,
            player: 'Alice',
            points: 9,
            wins: 3,
            losses: 1,
            draws: 0,
            omwp: 0.5,
            gwp: 0.5,
            ogwp: 0.5,
          },
        ],
        meta,
        page: { next_cursor: null, limit: 20 },
      },
      isLoading: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any)

    vi.mocked(useTournamentBracket).mockReturnValue({
      data: { data: [], meta, page: null },
      isLoading: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any)
  })

  it('shows the decks tab by default, linking to each deck', () => {
    renderPage()

    expect(screen.getByRole('link', { name: 'Alice' })).toHaveAttribute(
      'href',
      '/decks/d1',
    )
  })

  it('shows the commander(s) column for each deck', () => {
    renderPage()

    expect(screen.getByText('Tymna the Weaver')).toBeInTheDocument()
  })

  it('switches to the standings tab on click', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: 'Standings' }))

    expect(screen.getByText('9')).toBeInTheDocument()
  })

  it('shows an empty state on the bracket tab for a Swiss-only tournament', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: 'Bracket' }))

    expect(
      screen.getByText('No elimination bracket for this tournament (Swiss-only event).'),
    ).toBeInTheDocument()
  })
})
