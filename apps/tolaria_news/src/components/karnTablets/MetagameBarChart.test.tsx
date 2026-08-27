import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MetagameBarChart } from './MetagameBarChart'
import type { Archetype } from '@/schemas/karnTablets'

function archetype(overrides: Partial<Archetype> = {}): Archetype {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    name: overrides.name ?? 'Tasigur, the Golden Fang',
    commanders: overrides.commanders ?? [],
    deck_count: overrides.deck_count ?? 40,
    deck_share: overrides.deck_share ?? 0.2,
    deck_share_delta: overrides.deck_share_delta ?? null,
    momentum: overrides.momentum ?? 'stable',
  }
}

describe('MetagameBarChart', () => {
  it('shows a loading skeleton', () => {
    const { container } = render(
      <MetagameBarChart archetypes={undefined} isLoading={true} isError={false} />,
    )
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('shows an error message on failure', () => {
    render(<MetagameBarChart archetypes={undefined} isLoading={false} isError={true} />)
    expect(screen.getByText('Failed to load the metagame snapshot.')).toBeInTheDocument()
  })

  it('shows an empty-window message when there are no archetypes', () => {
    render(<MetagameBarChart archetypes={[]} isLoading={false} isError={false} />)
    expect(screen.getByText('No archetypes for this window.')).toBeInTheDocument()
  })

  it('renders one row per archetype with its share and deck count', () => {
    render(
      <MetagameBarChart
        archetypes={[
          archetype({
            name: 'Aragorn, King of Gondor',
            deck_share: 0.173,
            deck_count: 35,
          }),
          archetype({ name: 'Slimefoot and Squee', deck_share: 0.168, deck_count: 34 }),
        ]}
        isLoading={false}
        isError={false}
      />,
    )
    expect(screen.getByText('Aragorn, King of Gondor')).toBeInTheDocument()
    expect(screen.getByText('17.3% · 35')).toBeInTheDocument()
    expect(screen.getByText('16.8% · 34')).toBeInTheDocument()
  })

  it('labels each momentum classification', () => {
    render(
      <MetagameBarChart
        archetypes={[
          archetype({ name: 'Riser', momentum: 'rising', deck_share_delta: 0.02 }),
          archetype({ name: 'Faller', momentum: 'falling', deck_share_delta: -0.03 }),
          archetype({ name: 'Newcomer', momentum: 'new', deck_share_delta: null }),
          archetype({ name: 'Steady', momentum: 'stable', deck_share_delta: 0.001 }),
        ]}
        isLoading={false}
        isError={false}
      />,
    )
    expect(screen.getByText(/▲/)).toHaveTextContent('+2.0 pp')
    expect(screen.getByText(/▼/)).toHaveTextContent('−3.0 pp')
    expect(screen.getByText(/✦ new/)).toBeInTheDocument()
    expect(screen.getByText(/– steady/)).toBeInTheDocument()
  })

  it('gives the archetype name a commander-art hover when a scryfall id resolves', () => {
    render(
      <MetagameBarChart
        archetypes={[
          archetype({
            name: 'Tasigur, the Golden Fang',
            commanders: [{ name: 'Tasigur, the Golden Fang', scryfall_id: 'tasigur-id' }],
          }),
        ]}
        isLoading={false}
        isError={false}
      />,
    )
    // ArchetypeName renders the hover trigger as a dotted-underline span.
    const trigger = screen.getByText('Tasigur, the Golden Fang')
    expect(trigger).toHaveClass('decoration-dotted')
  })

  it('caps the chart at the top 20 archetypes', () => {
    const many = Array.from({ length: 25 }, (_, i) =>
      archetype({ name: `Archetype ${i.toString()}`, deck_count: 100 - i }),
    )
    render(<MetagameBarChart archetypes={many} isLoading={false} isError={false} />)
    expect(screen.getByRole('list').querySelectorAll('li')).toHaveLength(20)
    expect(screen.queryByText('Archetype 20')).not.toBeInTheDocument()
  })
})
