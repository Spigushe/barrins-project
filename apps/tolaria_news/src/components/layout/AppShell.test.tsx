import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AppShell } from './AppShell'

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

useTelemetryMock.mockReturnValue({ data: undefined, isLoading: true, isError: false })

describe('AppShell nav', () => {
  it('hides Karn Tablets links when the flag is off', () => {
    flagState.karnTabletsEnabled = false
    render(
      <MemoryRouter>
        <AppShell>content</AppShell>
      </MemoryRouter>,
    )

    expect(screen.queryByRole('link', { name: 'Metagame' })).not.toBeInTheDocument()
  })

  it('shows Karn Tablets links when the flag is on', () => {
    flagState.karnTabletsEnabled = true
    render(
      <MemoryRouter>
        <AppShell>content</AppShell>
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Metagame' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Archetypes' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Trends' })).toBeInTheDocument()
  })
})
