import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { LandingPage } from './LandingPage'

const flagState = vi.hoisted(() => ({ karnTabletsEnabled: false }))

vi.mock('@/lib/featureFlags', () => ({
  get karnTabletsEnabled() {
    return flagState.karnTabletsEnabled
  },
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  )
}

describe('LandingPage', () => {
  it('renders the headline and links the primary CTA to tournaments when Karn Tablets is off', () => {
    flagState.karnTabletsEnabled = false
    renderPage()

    expect(screen.getByText('Duel Commander,')).toBeInTheDocument()
    const cta = screen.getByRole('link', { name: /Browse tournaments/ })
    expect(cta).toHaveAttribute('href', '/tournaments')
    expect(screen.queryByText('archetypes mapped')).not.toBeInTheDocument()
  })

  it('links the primary CTA to /metagame and shows the archetypes stat when the flag is on', () => {
    flagState.karnTabletsEnabled = true
    renderPage()

    const cta = screen.getByRole('link', { name: /Explore the metagame/ })
    expect(cta).toHaveAttribute('href', '/metagame')
    expect(screen.getByText('archetypes mapped')).toBeInTheDocument()
  })
})
