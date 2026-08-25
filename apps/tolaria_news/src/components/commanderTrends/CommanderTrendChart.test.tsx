import { cloneElement, type ReactElement } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CommanderTrendChart } from './CommanderTrendChart'
import type { CommanderTrendSeries } from '@/schemas/tolariaNews'

// jsdom reports 0x0 for ResponsiveContainer's measured size, so recharts
// never renders its children -- a well-known recharts+jsdom limitation.
// Bypass sizing by cloning the chart with an explicit width/height
// instead, the standard workaround; every other recharts export (Legend,
// Line, Tooltip, ...) stays real.
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>()
  return {
    ...actual,
    ResponsiveContainer: ({
      children,
    }: {
      children: ReactElement<{ width?: number; height?: number }>
    }) => cloneElement(children, { width: 800, height: 400 }),
  }
})

const tymna = {
  name: 'Tymna the Weaver',
  scryfall_id: 'tymna-scryfall-id',
  color_identity: ['W', 'B'],
  mana_cost: '{1}{W}{B}',
  text: null,
  keywords: [],
}

const krark = {
  name: 'Krark, the Thumbless',
  scryfall_id: 'krark-scryfall-id',
  color_identity: ['U', 'R'],
  mana_cost: '{2}{U}{R}',
  text: null,
  keywords: [],
}

function series(name: string, count: number, deckCount: number): CommanderTrendSeries {
  return {
    commanders: [{ ...tymna, name }],
    total_deck_count: deckCount,
    points: Array.from({ length: count }, (_, i) => ({
      date_from: `2026-07-${(i * 7 + 1).toString().padStart(2, '0')}`,
      date_to: `2026-07-${(i * 7 + 7).toString().padStart(2, '0')}`,
      deck_count: deckCount,
    })),
  }
}

describe('CommanderTrendChart', () => {
  it('shows a loading skeleton', () => {
    const { container } = render(
      <CommanderTrendChart series={undefined} isLoading={true} isError={false} />,
    )

    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('shows an error message on failure', () => {
    render(<CommanderTrendChart series={undefined} isLoading={false} isError={true} />)

    expect(screen.getByText('Failed to load trending commanders.')).toBeInTheDocument()
  })

  it('shows an empty-window message when there is no data', () => {
    render(<CommanderTrendChart series={[]} isLoading={false} isError={false} />)

    expect(screen.getByText('No decks recorded in this window.')).toBeInTheDocument()
  })

  it('renders one legend entry per series, labeled with commanders and deck count', () => {
    render(
      <CommanderTrendChart
        series={[series('Tymna the Weaver', 2, 4), series('Krark, the Thumbless', 2, 2)]}
        isLoading={false}
        isError={false}
      />,
    )

    expect(screen.getByText('Tymna the Weaver (4)')).toBeInTheDocument()
    expect(screen.getByText('Krark, the Thumbless (2)')).toBeInTheDocument()
  })

  it('labels a partner pair with both commander names in one legend entry', () => {
    const pair: CommanderTrendSeries = {
      commanders: [tymna, krark],
      total_deck_count: 5,
      points: [{ date_from: '2026-07-01', date_to: '2026-07-07', deck_count: 5 }],
    }
    render(<CommanderTrendChart series={[pair]} isLoading={false} isError={false} />)

    expect(
      screen.getByText('Tymna the Weaver / Krark, the Thumbless (5)'),
    ).toBeInTheDocument()
  })
})
