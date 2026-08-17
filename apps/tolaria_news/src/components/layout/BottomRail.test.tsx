import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BottomRail } from './BottomRail'

const useTelemetryMock = vi.fn()

vi.mock('@/hooks/useTelemetry', () => ({
  useTelemetry: (): ReturnType<typeof useTelemetryMock> => useTelemetryMock(),
}))

function telemetry(nextBanlistAt: string, sourceSyncedAt: string | null) {
  return {
    data: {
      data: {
        season: {
          kind: 'banlist_period' as const,
          label: 'x',
          date_from: '2026-07-02',
          date_to: '2026-08-01',
        },
        season_year: 2026,
        season_number: 3,
        next_banlist_at: nextBanlistAt,
      },
      meta: { generated_at: '2026-08-01T00:00:00Z', source_synced_at: sourceSyncedAt },
      page: null,
    },
    isLoading: false,
    isError: false,
  }
}

describe('BottomRail', () => {
  beforeEach(() => {
    useTelemetryMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders nothing while telemetry is loading', () => {
    useTelemetryMock.mockReturnValue({ data: undefined, isLoading: true, isError: false })
    const { container } = render(<BottomRail />)

    expect(container).toBeEmptyDOMElement()
  })

  it('renders the season as <year>-<number>', () => {
    useTelemetryMock.mockReturnValue(telemetry('2026-09-28T18:00:00Z', null))
    render(<BottomRail />)

    expect(screen.getByText('Season · 2026-3')).toBeInTheDocument()
  })

  it('shows the last-sync relative time when source_synced_at is set', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-01T12:00:00Z'))
    useTelemetryMock.mockReturnValue(
      telemetry('2026-09-28T18:00:00Z', '2026-08-01T10:00:00Z'),
    )
    render(<BottomRail />)

    expect(screen.getByText('Synced 2 hours ago')).toBeInTheDocument()
  })

  it('shows "No data yet" when source_synced_at is null', () => {
    useTelemetryMock.mockReturnValue(telemetry('2026-09-28T18:00:00Z', null))
    render(<BottomRail />)

    expect(screen.getByText('No data yet')).toBeInTheDocument()
  })

  it('shows a static day count when next_banlist_at is a different Paris calendar day', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-01T12:00:00Z'))
    useTelemetryMock.mockReturnValue(telemetry('2026-08-04T18:00:00Z', null))
    render(<BottomRail />)

    expect(screen.getByText('Next banlist in 3 days')).toBeInTheDocument()
  })

  it('ticks a live HH:MM:SS countdown on the banlist day itself, before the effective time', () => {
    vi.useFakeTimers()
    // Same Paris calendar day (2026-08-02) as next_banlist_at, well before
    // its 20:00 Paris (18:00 UTC in August, CEST) effective time.
    vi.setSystemTime(new Date('2026-08-02T10:00:00Z'))
    useTelemetryMock.mockReturnValue(telemetry('2026-08-02T18:00:00Z', null))
    render(<BottomRail />)

    expect(screen.getByText('Next banlist in 08:00:00')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByText('Next banlist in 07:59:59')).toBeInTheDocument()
  })

  it('shows "Announcement published" once past the effective time, same Paris day', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-02T19:00:00Z'))
    useTelemetryMock.mockReturnValue(telemetry('2026-08-02T18:00:00Z', null))
    render(<BottomRail />)

    expect(screen.getByText('Announcement published')).toBeInTheDocument()
  })
})
