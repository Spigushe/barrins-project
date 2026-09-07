import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
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

const useMetagameMock = vi.fn()

vi.mock('@/hooks/useKarnTablets', () => ({
  useMetagame: (...args: unknown[]): ReturnType<typeof useMetagameMock> =>
    useMetagameMock(...args),
}))

const statsEnvelope = {
  data: { tournaments_count: 3184, decks_count: 96234, command_zones_count: 412 },
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

const cardRef = (name: string) => ({ name, scryfall_id: null })

const metagameEnvelope = {
  data: {
    format: 'Duel Commander',
    window: {
      kind: 'rolling_30d' as const,
      label: 'rolling_30d:2026-08-01',
      date_from: '2026-07-02',
      date_to: '2026-08-01',
    },
    previous_window: null,
    next_window: null,
    archetypes: [
      {
        id: 'a1',
        name: 'Tymna / Thrasios value',
        commanders: [cardRef('Tymna the Weaver'), cardRef('Thrasios, Triton Hero')],
        deck_count: 40,
        deck_share: 0.114,
        deck_share_delta: 0.005,
        momentum: 'stable' as const,
      },
      {
        id: 'a2',
        name: 'Najeela combo',
        commanders: [cardRef('Najeela, the Blade-Blossom')],
        deck_count: 20,
        deck_share: 0.08,
        deck_share_delta: 0.024,
        momentum: 'rising' as const,
      },
    ],
    fastest_rising: {
      id: 'a2',
      name: 'Najeela combo',
      commanders: [cardRef('Najeela, the Blade-Blossom')],
      deck_count: 20,
      deck_share: 0.08,
      deck_share_delta: 0.024,
      momentum: 'rising' as const,
    },
  },
  meta: { generated_at: '2026-08-01T00:00:00Z', source_synced_at: null },
  page: null,
}

const emptyMetagameEnvelope = {
  data: {
    ...metagameEnvelope.data,
    archetypes: [],
    fastest_rising: null,
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
    flagState.karnTabletsEnabled = false
    useTelemetryMock.mockReset()
    useTelemetryMock.mockReturnValue({ data: telemetryEnvelope, isLoading: false })
    useStatsMock.mockReset()
    useStatsMock.mockReturnValue({ data: statsEnvelope, isLoading: false })
    useMetagameMock.mockReset()
    useMetagameMock.mockReturnValue({ data: undefined, isLoading: false })
  })

  it('renders the headline and links the primary CTA to tournaments when Karn Tablets is off', () => {
    renderPage()

    expect(screen.getByText('Duel Commander,')).toBeInTheDocument()
    const cta = screen.getByRole('link', { name: /Browse tournaments/ })
    expect(cta).toHaveAttribute('href', '/tournaments')
    // The command-zones stat is always shown, flag or no flag.
    expect(screen.getByText('command zones charted')).toBeInTheDocument()
    expect(screen.queryByText('archetypes mapped')).not.toBeInTheDocument()

    const methodologyCta = screen.getByRole('link', { name: 'Read the methodology' })
    expect(methodologyCta).toHaveAttribute('href', '/methodology')
  })

  it('shows real tournament / command-zone / deck counts from useStats, comma-formatted', () => {
    renderPage()

    expect(screen.getByText('3,184')).toBeInTheDocument()
    expect(screen.getByText('412')).toBeInTheDocument()
    expect(screen.getByText('96,234')).toBeInTheDocument()
  })

  it('shows a placeholder dash for all three counts while stats are loading', () => {
    useStatsMock.mockReturnValue({ data: undefined, isLoading: true })
    renderPage()

    expect(screen.getAllByText('—')).toHaveLength(3)
  })

  it('shows the eyebrow with the injected monorepo version', () => {
    renderPage()

    expect(screen.getByText(`Duel Commander · v${__APP_VERSION__}`)).toBeInTheDocument()
  })

  it('links the primary CTA to /metagame and still shows the command-zones stat when the flag is on', () => {
    flagState.karnTabletsEnabled = true
    useMetagameMock.mockReturnValue({ data: metagameEnvelope, isLoading: false })
    renderPage()

    const cta = screen.getByRole('link', { name: /Explore the metagame/ })
    expect(cta).toHaveAttribute('href', '/metagame')
    expect(screen.getByText('command zones charted')).toBeInTheDocument()

    expect(screen.getByRole('link', { name: 'Read the methodology' })).toHaveAttribute(
      'href',
      '/methodology',
    )
  })

  describe('the "decoded." easter-egg trigger', () => {
    function renderWithHiddenRoute() {
      return render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/west" element={<div>hidden calculator</div>} />
          </Routes>
        </MemoryRouter>,
      )
    }

    it('opens the hidden calculator on the seventh click of "decoded."', async () => {
      flagState.karnTabletsEnabled = false
      const user = userEvent.setup()
      renderWithHiddenRoute()

      const word = screen.getByText('decoded.')
      for (let i = 0; i < 7; i++) await user.click(word)

      expect(await screen.findByText('hidden calculator')).toBeInTheDocument()
    })

    it('stays closed before the seventh click', async () => {
      const user = userEvent.setup()
      renderWithHiddenRoute()

      const word = screen.getByText('decoded.')
      for (let i = 0; i < 6; i++) await user.click(word)

      expect(screen.queryByText('hidden calculator')).not.toBeInTheDocument()
    })
  })

  describe('VizPanel Karn Tablets callouts', () => {
    it('renders the top-archetype and fastest-rising callouts from the metagame snapshot', () => {
      flagState.karnTabletsEnabled = true
      useMetagameMock.mockReturnValue({ data: metagameEnvelope, isLoading: false })
      renderPage()

      // #1 archetype by share.
      expect(
        screen.getByText(/cluster · Tymna the Weaver \/ Thrasios, Triton Hero/),
      ).toBeInTheDocument()
      expect(screen.getByText('share 11.4%')).toBeInTheDocument()
      // Fastest riser (backend-selected, not the biggest archetype).
      expect(screen.getByText(/rising · Najeela, the Blade-Blossom/)).toBeInTheDocument()
      expect(screen.getByText('share ↑ 2.4 pts')).toBeInTheDocument()
      // The still-static macro-archetype callout.
      expect(screen.getByText('n = 286')).toBeInTheDocument()
    })

    it('hides both data-driven callouts when there is no clustering run yet', () => {
      flagState.karnTabletsEnabled = true
      useMetagameMock.mockReturnValue({
        data: emptyMetagameEnvelope,
        isLoading: false,
      })
      renderPage()

      expect(screen.queryByText(/^cluster · /)).not.toBeInTheDocument()
      expect(screen.queryByText(/^rising · /)).not.toBeInTheDocument()
      // The static one still renders.
      expect(screen.getByText('n = 286')).toBeInTheDocument()
    })

    it('renders no callouts at all when the flag is off', () => {
      useMetagameMock.mockReturnValue({ data: metagameEnvelope, isLoading: false })
      renderPage()

      expect(screen.queryByText('n = 286')).not.toBeInTheDocument()
      expect(screen.queryByText(/^cluster · /)).not.toBeInTheDocument()
    })
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
