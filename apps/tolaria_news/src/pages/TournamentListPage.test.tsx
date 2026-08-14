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
})
