import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DecklistsPage } from './DecklistsPage'

const meta = { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null }

const page1 = {
  data: [
    {
      id: 'd1',
      tournament_id: 't1',
      date: '2026-08-02',
      player: 'A. Nakamura',
      result: '1',
      anchor_uri: 'https://x#deck_a',
      tournament_name: 'Duel Commander Open',
      tournament_source: 'mtgtop8',
    },
  ],
  meta,
  page: { next_cursor: 'abc', limit: 20 },
}

const page2 = {
  data: [
    {
      id: 'd2',
      tournament_id: 't2',
      date: '2026-08-01',
      player: 'B. Costa',
      result: null,
      anchor_uri: 'https://y#deck_b',
      tournament_name: 'Another Duel Commander event',
      tournament_source: 'mtgo',
    },
  ],
  meta,
  page: { next_cursor: null, limit: 20 },
}

const commandersMeta = { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null }

const useDecksMock = vi.fn()
const useCommandersMock = vi.fn()
const useStaplesMock = vi.fn()

vi.mock('@/hooks/useDecks', () => ({
  useDecks: (
    filters: unknown,
    cursor: string | undefined,
  ): ReturnType<typeof useDecksMock> => useDecksMock(filters, cursor),
  useCommanders: (): ReturnType<typeof useCommandersMock> => useCommandersMock(),
  useStaples: (
    dateFrom: unknown,
    dateTo: unknown,
    commander: unknown,
    enabled: unknown,
  ): ReturnType<typeof useStaplesMock> =>
    useStaplesMock(dateFrom, dateTo, commander, enabled),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <DecklistsPage />
    </MemoryRouter>,
  )
}

describe('DecklistsPage', () => {
  beforeEach(() => {
    useDecksMock.mockReset()
    useDecksMock.mockImplementation((_filters: unknown, cursor?: string) => ({
      data: cursor === 'abc' ? page2 : page1,
      isLoading: false,
      isError: false,
      error: null,
    }))
    useCommandersMock.mockReset()
    useCommandersMock.mockReturnValue({
      data: { data: ['Kraum, Ludevic’s Opus', 'Tymna the Weaver'], meta: commandersMeta },
      isLoading: false,
    })
    useStaplesMock.mockReset()
    useStaplesMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    })
  })

  it('renders decklist rows with pilot/tournament links and a source badge', () => {
    renderPage()

    expect(screen.getByRole('link', { name: 'A. Nakamura' })).toHaveAttribute(
      'href',
      '/decks/d1',
    )
    expect(screen.getByRole('link', { name: 'Duel Commander Open' })).toHaveAttribute(
      'href',
      '/tournaments/t1',
    )
    expect(screen.getByText('mtgtop8')).toBeInTheDocument()
  })

  it('advances to the next page using the returned cursor', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Next' }))

    expect(screen.getByRole('link', { name: 'B. Costa' })).toBeInTheDocument()
  })

  it('shows an empty state when no decklists match the filters', () => {
    useDecksMock.mockReturnValue({
      data: { data: [], meta, page: null },
      isLoading: false,
      isError: false,
      error: null,
    })
    renderPage()

    expect(screen.getByText('No decklists match these filters.')).toBeInTheDocument()
  })

  it('commits the pilot filter on Enter and resets pagination', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.type(
      screen.getByPlaceholderText('Search by pilot name'),
      'nakamura{Enter}',
    )

    expect(useDecksMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ player: 'nakamura' }),
      undefined,
    )
  })

  it('filters by the selected commander', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.selectOptions(screen.getByLabelText('Commander'), 'Tymna the Weaver')

    expect(useDecksMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ commander: 'Tymna the Weaver' }),
      undefined,
    )
  })

  it('shows a loading placeholder while commanders are fetching', () => {
    useCommandersMock.mockReturnValue({ data: undefined, isLoading: true })
    renderPage()

    expect(screen.getByRole('option', { name: 'Loading…' })).toBeInTheDocument()
    expect(screen.getByLabelText('Commander')).toBeDisabled()
  })

  it('toggles color pips into and out of the colors filter, multi-select', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Color identity: W' }))
    expect(useDecksMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ colors: ['W'] }),
      undefined,
    )

    await user.click(screen.getByRole('button', { name: 'Color identity: U' }))
    expect(useDecksMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ colors: ['W', 'U'] }),
      undefined,
    )

    await user.click(screen.getByRole('button', { name: 'Color identity: W' }))
    expect(useDecksMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ colors: ['U'] }),
      undefined,
    )
  })

  it('toggles size chips into and out of the sizes filter, multi-select', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Tournament size: Leagues' }))
    expect(useDecksMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ sizes: ['leagues'] }),
      undefined,
    )

    await user.click(screen.getByRole('button', { name: 'Tournament size: 100+' }))
    expect(useDecksMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ sizes: ['leagues', 'major'] }),
      undefined,
    )

    await user.click(screen.getByRole('button', { name: 'Tournament size: Leagues' }))
    expect(useDecksMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ sizes: ['major'] }),
      undefined,
    )
  })

  describe('staples panel', () => {
    it('is hidden until a commander filter is selected', () => {
      renderPage()

      expect(useStaplesMock).toHaveBeenLastCalledWith(
        undefined,
        undefined,
        undefined,
        false,
      )
      expect(screen.queryByText(/Staples for/)).not.toBeInTheDocument()
    })

    it('fetches and shows staples scoped to the selected commander', async () => {
      const user = userEvent.setup()
      useStaplesMock.mockReturnValue({
        data: {
          data: {
            date_from: '2015-11-01',
            date_to: '2026-08-19',
            commander: 'Tymna the Weaver',
            tournaments_considered: 3,
            decks_considered: 4,
            min_percentage: 65,
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
          meta,
          page: null,
        },
        isLoading: false,
        isError: false,
        error: null,
      })
      renderPage()

      await user.selectOptions(screen.getByLabelText('Commander'), 'Tymna the Weaver')

      expect(useStaplesMock).toHaveBeenLastCalledWith(
        undefined,
        undefined,
        'Tymna the Weaver',
        true,
      )
      expect(screen.getByText('Staples for Tymna the Weaver')).toBeInTheDocument()
      expect(screen.getByAltText('Sol Ring')).toBeInTheDocument()
      expect(screen.getByText('75% of decks')).toBeInTheDocument()
    })
  })

  describe('reset filters', () => {
    it('is disabled when filters are already at their defaults', () => {
      renderPage()

      expect(screen.getByRole('button', { name: 'Reset filters' })).toBeDisabled()
    })

    it('clears the pilot input, filters, and staples panel', async () => {
      const user = userEvent.setup()
      renderPage()

      await user.type(screen.getByPlaceholderText('Search by pilot name'), 'nakamura')
      await user.selectOptions(screen.getByLabelText('Commander'), 'Tymna the Weaver')
      expect(screen.getByRole('button', { name: 'Reset filters' })).toBeEnabled()

      await user.click(screen.getByRole('button', { name: 'Reset filters' }))

      expect(screen.getByRole('button', { name: 'Reset filters' })).toBeDisabled()
      expect(screen.getByPlaceholderText('Search by pilot name')).toHaveValue('')
      expect(useDecksMock).toHaveBeenLastCalledWith({}, undefined)
      expect(screen.queryByText(/Staples for/)).not.toBeInTheDocument()
    })
  })
})
