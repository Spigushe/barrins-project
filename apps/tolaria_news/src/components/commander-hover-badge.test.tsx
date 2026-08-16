import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CommanderHoverBadge } from './commander-hover-badge'
import type { CommanderRef } from '@/schemas/tolariaNews'

const tymna: CommanderRef = {
  name: 'Tymna the Weaver',
  scryfall_id: 'tymna-scryfall-id',
  color_identity: ['W', 'B'],
  mana_cost: '{1}{W}{B}',
  text: null,
  keywords: [],
}

const kraum: CommanderRef = {
  name: "Kraum, Ludevic's Opus",
  scryfall_id: 'kraum-scryfall-id',
  color_identity: ['U', 'R'],
  mana_cost: '{1}{U}{R}',
  text: null,
  keywords: [],
}

const unresolved: CommanderRef = {
  name: 'Some Unresolvable Card',
  scryfall_id: null,
  color_identity: [],
  mana_cost: null,
  text: null,
  keywords: [],
}

describe('CommanderHoverBadge', () => {
  it('renders nothing for an empty commander list', () => {
    const { container } = render(<CommanderHoverBadge commanders={[]} />)

    expect(container).toBeEmptyDOMElement()
  })

  it('renders one badge for a solo commander', () => {
    render(<CommanderHoverBadge commanders={[tymna]} />)

    expect(screen.getByText('Tymna the Weaver')).toBeInTheDocument()
  })

  it('renders both badges for a partner pair', () => {
    render(<CommanderHoverBadge commanders={[tymna, kraum]} />)

    expect(screen.getByText('Tymna the Weaver')).toBeInTheDocument()
    expect(screen.getByText("Kraum, Ludevic's Opus")).toBeInTheDocument()
  })

  it('falls back to a plain badge (no hover trigger) when scryfall_id is missing', () => {
    render(<CommanderHoverBadge commanders={[unresolved]} />)

    expect(screen.getByText('Some Unresolvable Card')).toBeInTheDocument()
  })
})
