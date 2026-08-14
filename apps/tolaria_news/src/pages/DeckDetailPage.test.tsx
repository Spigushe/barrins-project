import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { DeckDetailPage } from './DeckDetailPage'
import { useDeck } from '@/hooks/useDecks'

vi.mock('@/hooks/useDecks', () => ({
  useDeck: vi.fn(),
}))

const meta = { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null }

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/decks/d1']}>
      <Routes>
        <Route path="/decks/:id" element={<DeckDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DeckDetailPage', () => {
  it('renders resolved commanders and mainboard cards', () => {
    vi.mocked(useDeck).mockReturnValue({
      data: {
        data: {
          id: 'd1',
          tournament_id: 't1',
          date: '2026-08-01',
          player: 'Alice',
          result: '3-1',
          anchor_uri: 'x',
          notes: null,
          commanders: [
            { name: 'Krenko, Mob Boss', scryfall_id: null, color_identity: ['R'] },
          ],
          mainboard: [
            {
              name: 'Sol Ring',
              qty: 1,
              cmc: 1,
              type_line: 'Artifact',
              scryfall_id: null,
            },
          ],
        },
        meta,
        page: null,
      },
      isLoading: false,
      isError: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any)

    renderPage()

    expect(screen.getByText('Krenko, Mob Boss')).toBeInTheDocument()
    expect(screen.getByText('Sol Ring')).toBeInTheDocument()
  })

  it('renders no commander badge for a non-Commander deck', () => {
    vi.mocked(useDeck).mockReturnValue({
      data: {
        data: {
          id: 'd2',
          tournament_id: 't1',
          date: '2026-08-01',
          player: 'Bob',
          result: null,
          anchor_uri: 'x',
          notes: null,
          commanders: [],
          mainboard: [],
        },
        meta,
        page: null,
      },
      isLoading: false,
      isError: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any)

    renderPage()

    expect(screen.getByText('Bob')).toBeInTheDocument()
    expect(screen.queryByText('Krenko, Mob Boss')).not.toBeInTheDocument()
  })
})
