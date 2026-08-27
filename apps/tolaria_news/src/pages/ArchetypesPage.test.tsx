import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ArchetypesPage } from './ArchetypesPage'
import type { ArchetypeDetailPage, Window } from '@/schemas/karnTablets'

const meta = { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null }

function window_(label: string): Window {
  return {
    kind: 'banlist_period',
    label,
    date_from: '2026-01-27',
    date_to: '2026-03-30',
  }
}

function detailPage(
  name: string,
  windows: Partial<Pick<ArchetypeDetailPage, 'previous_window' | 'next_window'>> = {},
): ArchetypeDetailPage {
  return {
    format: 'Duel Commander',
    window: window_('banlist_period:current'),
    previous_window: windows.previous_window ?? null,
    next_window: windows.next_window ?? null,
    archetypes: [
      {
        id: name,
        name,
        commanders: [],
        deck_count: 30,
        deck_share: 0.3,
        deck_share_delta: null,
        momentum: 'stable',
        representative_mainboard: [
          {
            name: 'Brainstorm',
            qty: 1,
            scryfall_id: null,
            is_land: false,
            is_signature: true,
          },
        ],
      },
    ],
  }
}

const page1 = {
  data: detailPage('Tasigur, the Golden Fang', {
    previous_window: window_('banlist_period:older'),
  }),
  meta,
  page: { next_cursor: 'cursor-2', limit: 20 },
}
const page2 = {
  data: detailPage('Aragorn, King of Gondor', {
    previous_window: window_('banlist_period:older'),
  }),
  meta,
  page: { next_cursor: null, limit: 20 },
}
const olderWindowPage = {
  data: detailPage('Older-period archetype', {
    next_window: window_('banlist_period:current'),
  }),
  meta,
  page: { next_cursor: null, limit: 20 },
}

const useArchetypesMock = vi.fn()

vi.mock('@/hooks/useKarnTablets', () => ({
  useArchetypes: (
    windowMode: string,
    at: string | undefined,
    cursor: string | undefined,
  ): ReturnType<typeof useArchetypesMock> => useArchetypesMock(windowMode, at, cursor),
}))

describe('ArchetypesPage', () => {
  beforeEach(() => {
    useArchetypesMock.mockReset()
    useArchetypesMock.mockImplementation(
      (_window: string, at?: string, cursor?: string) => ({
        data:
          at === 'banlist_period:older'
            ? olderWindowPage
            : cursor === 'cursor-2'
              ? page2
              : page1,
        isLoading: false,
        isError: false,
      }),
    )
  })

  it('defaults to the banlist-period window and the latest period', () => {
    render(<ArchetypesPage />)
    expect(useArchetypesMock).toHaveBeenCalledWith('banlist_period', undefined, undefined)
  })

  it('pages forward and back with the cursor', async () => {
    const user = userEvent.setup()
    render(<ArchetypesPage />)

    expect(screen.getByText('Tasigur, the Golden Fang')).toBeInTheDocument()
    expect(screen.getByText('Page 1')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Next' }))

    expect(useArchetypesMock).toHaveBeenLastCalledWith(
      'banlist_period',
      undefined,
      'cursor-2',
    )
    expect(screen.getByText('Aragorn, King of Gondor')).toBeInTheDocument()
    expect(screen.getByText('Page 2')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Previous' }))
    expect(screen.getByText('Page 1')).toBeInTheDocument()
  })

  it('steps to the previous period and resets pagination', async () => {
    const user = userEvent.setup()
    render(<ArchetypesPage />)

    // Advance a page first so the reset is observable.
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Page 2')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '← Previous period' }))

    expect(useArchetypesMock).toHaveBeenLastCalledWith(
      'banlist_period',
      'banlist_period:older',
      undefined,
    )
    expect(screen.getByText('Older-period archetype')).toBeInTheDocument()
  })

  it('disables the period steppers at the ends of the range', () => {
    render(<ArchetypesPage />)
    // page1 has a previous_window but no next_window.
    expect(screen.getByRole('button', { name: '← Previous period' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Next period →' })).toBeDisabled()
  })
})
