import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ArchetypeDetailTable } from './ArchetypeDetailTable'
import type { MetagameArchetypeDetail, RepresentativeCard } from '@/schemas/karnTablets'

function card(
  name: string,
  qty: number,
  overrides: Partial<RepresentativeCard> = {},
): RepresentativeCard {
  return {
    name,
    qty,
    scryfall_id: overrides.scryfall_id ?? null,
    is_land: overrides.is_land ?? false,
    // Default mirrors the backend: non-lands are always signature.
    is_signature: overrides.is_signature ?? !(overrides.is_land ?? false),
  }
}

function detail(
  overrides: Partial<MetagameArchetypeDetail> = {},
): MetagameArchetypeDetail {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    name: overrides.name ?? 'Tasigur, the Golden Fang',
    commanders: overrides.commanders ?? [],
    deck_count: overrides.deck_count ?? 40,
    deck_share: overrides.deck_share ?? 0.2,
    deck_share_delta: overrides.deck_share_delta ?? null,
    momentum: overrides.momentum ?? 'stable',
    representative_mainboard: overrides.representative_mainboard ?? [
      card('Brainstorm', 1),
      card('Island', 8, { is_land: true, is_signature: false }),
    ],
  }
}

describe('ArchetypeDetailTable', () => {
  it('shows a loading skeleton', () => {
    const { container } = render(
      <ArchetypeDetailTable archetypes={undefined} isLoading={true} isError={false} />,
    )
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('shows an error message on failure', () => {
    render(
      <ArchetypeDetailTable archetypes={undefined} isLoading={false} isError={true} />,
    )
    expect(screen.getByText('Failed to load archetype detail.')).toBeInTheDocument()
  })

  it('reports the representative list as distinct/total card counts', () => {
    render(
      <ArchetypeDetailTable
        archetypes={[
          detail({
            representative_mainboard: [
              card('Brainstorm', 1),
              card('Ponder', 1),
              card('Island', 10, { is_land: true, is_signature: false }),
            ],
          }),
        ]}
        isLoading={false}
        isError={false}
      />,
    )
    // 3 distinct names, 12 cards total.
    expect(screen.getByText('3/12')).toBeInTheDocument()
  })

  it('renders only backend-flagged signature cards, capped at six', () => {
    render(
      <ArchetypeDetailTable
        archetypes={[
          detail({
            representative_mainboard: [
              card('Swamp', 12, { is_land: true, is_signature: false }),
              card('Abrupt Decay', 1),
              card('Brainstorm', 1),
              card('Fatal Push', 1),
              card('Thoughtseize', 1),
              card('Deathrite Shaman', 1),
              card('Snapcaster Mage', 1),
              card('Kolaghan Command', 1),
            ],
          }),
        ]}
        isLoading={false}
        isError={false}
      />,
    )
    const row = screen.getByText('Abrupt Decay').closest('td')
    expect(row).toHaveTextContent(
      'Abrupt Decay, Brainstorm, Fatal Push, Thoughtseize, Deathrite Shaman, Snapcaster Mage',
    )
    expect(row).not.toHaveTextContent('Swamp')
    expect(row).not.toHaveTextContent('Kolaghan Command')
  })

  it('keeps an archetype-defining land the backend marked signature', () => {
    render(
      <ArchetypeDetailTable
        archetypes={[
          detail({
            representative_mainboard: [
              card('Gaea’s Cradle', 1, { is_land: true, is_signature: true }),
              card('Swamp', 12, { is_land: true, is_signature: false }),
            ],
          }),
        ]}
        isLoading={false}
        isError={false}
      />,
    )
    const row = screen.getByText('Gaea’s Cradle').closest('td')
    expect(row).not.toHaveTextContent('Swamp')
  })

  it('gives a signature card a Scryfall-art hover when its id resolves', () => {
    render(
      <ArchetypeDetailTable
        archetypes={[
          detail({
            representative_mainboard: [
              card('Brainstorm', 1, { scryfall_id: 'brainstorm-id' }),
            ],
          }),
        ]}
        isLoading={false}
        isError={false}
      />,
    )
    expect(screen.getByText('Brainstorm')).toHaveClass('underline')
  })

  it('shows an empty-window row when there are no archetypes', () => {
    render(<ArchetypeDetailTable archetypes={[]} isLoading={false} isError={false} />)
    expect(screen.getByText('No archetypes for this window.')).toBeInTheDocument()
  })
})
