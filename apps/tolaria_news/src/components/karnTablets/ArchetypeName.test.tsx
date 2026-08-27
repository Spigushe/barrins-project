import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ArchetypeName } from './ArchetypeName'

describe('ArchetypeName', () => {
  it('renders plain text when no commander resolves', () => {
    render(<ArchetypeName name="Mystery Brew #2" commanders={[]} />)
    const el = screen.getByText('Mystery Brew #2')
    expect(el.tagName).toBe('SPAN')
    expect(el).not.toHaveClass('underline')
  })

  it('renders plain text when commanders have no scryfall id', () => {
    render(
      <ArchetypeName
        name="Unresolved"
        commanders={[{ name: 'Unresolved', scryfall_id: null }]}
      />,
    )
    expect(screen.getByText('Unresolved')).not.toHaveClass('underline')
  })

  it('shows a hover trigger when a commander resolves', () => {
    render(
      <ArchetypeName
        name="Tymna / Kraum"
        commanders={[
          { name: 'Tymna the Weaver', scryfall_id: 'tymna-id' },
          { name: 'Kraum, Ludevic’s Opus', scryfall_id: null },
        ]}
      />,
    )
    expect(screen.getByText('Tymna / Kraum')).toHaveClass('underline')
  })
})
