import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ArchetypeFacetGrid } from './ArchetypeFacetGrid'
import type { Trend, TrendPoint } from '@/schemas/karnTablets'

function point(month: number, deck_share: number | null): TrendPoint {
  const mm = month.toString().padStart(2, '0')
  return {
    window: {
      kind: 'banlist_period',
      label: `banlist_period:2026-${mm}`,
      date_from: `2026-${mm}-01`,
      date_to: `2026-${mm}-28`,
    },
    deck_share,
  }
}

function trend(name: string, shares: (number | null)[]): Trend {
  return {
    archetype_id: crypto.randomUUID(),
    archetype_name: name,
    commanders: [],
    points: shares.map((s, i) => point(i + 1, s)),
  }
}

describe('ArchetypeFacetGrid', () => {
  it('shows a loading skeleton', () => {
    const { container } = render(
      <ArchetypeFacetGrid trends={undefined} isLoading={true} isError={false} />,
    )
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('shows an error message on failure', () => {
    render(<ArchetypeFacetGrid trends={undefined} isLoading={false} isError={true} />)
    expect(screen.getByText('Failed to load archetype trends.')).toBeInTheDocument()
  })

  it('asks for more runs when no series has two points', () => {
    render(
      <ArchetypeFacetGrid
        trends={[trend('Tasigur', [0.2])]}
        isLoading={false}
        isError={false}
      />,
    )
    expect(
      screen.getByText('Not enough runs yet to chart per-archetype movement.'),
    ).toBeInTheDocument()
  })

  it('renders one panel per archetype, capped at ten', () => {
    const many = Array.from({ length: 20 }, (_, i) =>
      trend(`Archetype ${i.toString()}`, [0.1, 0.2, 0.15]),
    )
    render(<ArchetypeFacetGrid trends={many} isLoading={false} isError={false} />)
    expect(screen.getAllByRole('img')).toHaveLength(10)
    expect(screen.queryByText('Archetype 10')).not.toBeInTheDocument()
  })

  it('breaks the line into segments around a missing period', () => {
    const { container } = render(
      <ArchetypeFacetGrid
        trends={[trend('Gappy', [0.2, null, 0.25, 0.3])]}
        isLoading={false}
        isError={false}
      />,
    )
    const linePath = container.querySelector('path[stroke="var(--color-accent)"]')
    // Two draw commands -> the null period split the line in two.
    expect(linePath?.getAttribute('d')?.match(/M/g)).toHaveLength(2)
  })

  it('summarises presence, peak and latest share per panel', () => {
    render(
      <ArchetypeFacetGrid
        trends={[trend('Gappy', [0.2, null, 0.25, 0.3])]}
        isLoading={false}
        isError={false}
      />,
    )
    expect(
      screen.getByText('3/4 periods · peak 30.0% · latest 30.0%'),
    ).toBeInTheDocument()
  })
})
