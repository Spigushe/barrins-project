import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LandingPage } from './LandingPage'

const flagState = vi.hoisted(() => ({ karnTabletsEnabled: false }))

vi.mock('@/lib/featureFlags', () => ({
  get karnTabletsEnabled() {
    return flagState.karnTabletsEnabled
  },
}))

const useTelemetryMock = vi.fn()

vi.mock('@/hooks/useTelemetry', () => ({
  useTelemetry: (): ReturnType<typeof useTelemetryMock> => useTelemetryMock(),
}))

const useStatsMock = vi.fn()

vi.mock('@/hooks/useStats', () => ({
  useStats: (): ReturnType<typeof useStatsMock> => useStatsMock(),
}))

const statsEnvelope = {
  data: { tournaments_count: 3184, decks_count: 96234 },
  meta: { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null },
  page: null,
}

const telemetryEnvelope = {
  data: {
    season: {
      kind: 'banlist_period' as const,
      label: 'x',
      date_from: '2026-07-02',
      date_to: '2026-08-01',
    },
    season_year: 2026,
    season_number: 3,
    next_banlist_at: '2026-08-02T18:00:00Z',
  },
  meta: { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null },
  page: null,
}

function renderPage() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  )
}

describe('LandingPage', () => {
  beforeEach(() => {
    useTelemetryMock.mockReset()
    useTelemetryMock.mockReturnValue({ data: telemetryEnvelope, isLoading: false })
    useStatsMock.mockReset()
    useStatsMock.mockReturnValue({ data: statsEnvelope, isLoading: false })
  })

  it('renders the headline and links the primary CTA to tournaments when Karn Tablets is off', () => {
    flagState.karnTabletsEnabled = false
    renderPage()

    expect(screen.getByText('Duel Commander,')).toBeInTheDocument()
    const cta = screen.getByRole('link', { name: /Browse tournaments/ })
    expect(cta).toHaveAttribute('href', '/tournaments')
    expect(screen.queryByText('archetypes mapped')).not.toBeInTheDocument()

    const methodologyCta = screen.getByRole('link', { name: 'Read the methodology' })
    expect(methodologyCta).toHaveAttribute('href', '/methodology')
  })

  it('shows real tournament/deck counts from useStats, comma-formatted', () => {
    renderPage()

    expect(screen.getByText('3,184')).toBeInTheDocument()
    expect(screen.getByText('96,234')).toBeInTheDocument()
  })

  it('shows a placeholder dash for counts while stats are loading', () => {
    useStatsMock.mockReturnValue({ data: undefined, isLoading: true })
    renderPage()

    expect(screen.getAllByText('—')).toHaveLength(2)
  })

  it('shows the eyebrow with the injected monorepo version', () => {
    renderPage()

    expect(screen.getByText(`Duel Commander · v${__APP_VERSION__}`)).toBeInTheDocument()
  })

  it('links the primary CTA to /metagame and shows the archetypes stat when the flag is on', () => {
    flagState.karnTabletsEnabled = true
    renderPage()

    const cta = screen.getByRole('link', { name: /Explore the metagame/ })
    expect(cta).toHaveAttribute('href', '/metagame')
    expect(screen.getByText('archetypes mapped')).toBeInTheDocument()

    expect(screen.getByRole('link', { name: 'Read the methodology' })).toHaveAttribute(
      'href',
      '/methodology',
    )
  })

  describe('VizPanel season label', () => {
    it('renders the year-number season label once telemetry has loaded', () => {
      useTelemetryMock.mockReturnValue({ data: telemetryEnvelope, isLoading: false })
      renderPage()

      expect(screen.getByText(/meta-graph · 2026-3/)).toBeInTheDocument()
    })

    it('shows plain "meta-graph" with no trailing number while loading', () => {
      useTelemetryMock.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
      })
      renderPage()

      expect(screen.getByText('meta-graph')).toBeInTheDocument()
    })
  })
})
