import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { FeatureGate } from './FeatureGate'

const flagState = vi.hoisted(() => ({ karnTabletsEnabled: false }))

vi.mock('@/lib/featureFlags', () => ({
  get karnTabletsEnabled() {
    return flagState.karnTabletsEnabled
  },
}))

function renderWithGate(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/metagame"
          element={
            <FeatureGate>
              <div>Metagame content</div>
            </FeatureGate>
          }
        />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('FeatureGate', () => {
  it('redirects to / when VITE_FEATURE_KARN_TABLETS is off', () => {
    flagState.karnTabletsEnabled = false
    renderWithGate('/metagame')

    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.queryByText('Metagame content')).not.toBeInTheDocument()
  })

  it('renders the gated content when the flag is on', () => {
    flagState.karnTabletsEnabled = true
    renderWithGate('/metagame')

    expect(screen.getByText('Metagame content')).toBeInTheDocument()
  })
})
