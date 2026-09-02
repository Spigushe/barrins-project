import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminMetricsPage } from './AdminMetricsPage'

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminMetricsPage />
    </MemoryRouter>,
  )
}

type Bucket = { period_start: string; count: number }
type Series = { daily: Bucket[]; weekly: Bucket[]; monthly: Bucket[] }

let platformMetrics:
  | {
      total_personal_decks: { value: number; source: string }
      total_matches: { value: number; source: string }
    }
  | undefined

let platformMetricsTimeseries:
  { personal_decks: Series; matches: Series } | undefined

vi.mock('@/hooks/useAdmin', () => ({
  usePlatformMetrics: () => ({
    data: platformMetrics,
    isLoading: false,
    isError: false,
  }),
  usePlatformMetricsTimeseries: () => ({
    data: platformMetricsTimeseries,
    isLoading: false,
    isError: false,
  }),
}))

beforeEach(() => {
  platformMetrics = {
    total_personal_decks: { value: 7, source: 'tamiyo_scroll' },
    total_matches: { value: 13, source: 'tamiyo_scroll' },
  }
  platformMetricsTimeseries = {
    personal_decks: {
      daily: [{ period_start: '2026-08-01T00:00:00Z', count: 1 }],
      weekly: [{ period_start: '2026-07-27T00:00:00Z', count: 2 }],
      monthly: [{ period_start: '2026-08-01T00:00:00Z', count: 3 }],
    },
    matches: {
      daily: [{ period_start: '2026-08-01T00:00:00Z', count: 4 }],
      weekly: [{ period_start: '2026-07-27T00:00:00Z', count: 6 }],
      monthly: [{ period_start: '2026-08-01T00:00:00Z', count: 8 }],
    },
  }
})

describe('AdminMetricsPage', () => {
  it('renders the flat all-time totals as tiles (no "accounts" tile since ADR-20)', () => {
    renderPage()

    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('13')).toBeInTheDocument()
    expect(screen.queryByText('Accounts created')).not.toBeInTheDocument()
    expect(screen.getByText('Personal decks created')).toBeInTheDocument()
    expect(screen.getByText('Matches recorded')).toBeInTheDocument()
  })

  it('renders one time-comparison chart per metric, defaulting to the daily view', () => {
    renderPage()

    expect(screen.getByText('Evolution over time')).toBeInTheDocument()
    expect(screen.queryByText('New accounts')).not.toBeInTheDocument()
    expect(screen.getByText('New personal decks')).toBeInTheDocument()
    expect(screen.getByText('New matches')).toBeInTheDocument()
    expect(screen.getAllByText('Day-by-day evolution')).toHaveLength(2)
  })

  it('switches all charts to the weekly view when the Week tab is selected', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('tab', { name: 'Week' }))

    expect(screen.getAllByText('Week-by-week evolution')).toHaveLength(2)
  })

  it('shows an empty-state message for a metric with no buckets in the selected window', () => {
    platformMetricsTimeseries = {
      ...platformMetricsTimeseries!,
      matches: { daily: [], weekly: [], monthly: [] },
    }
    renderPage()

    const matchesTitle = screen.getByText('New matches')
    const matchesCard = matchesTitle.parentElement as HTMLElement
    expect(
      within(matchesCard).getByText('No data in this window yet.'),
    ).toBeInTheDocument()
  })
})
