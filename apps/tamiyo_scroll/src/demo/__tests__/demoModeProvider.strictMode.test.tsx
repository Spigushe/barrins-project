import { StrictMode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { usePersonalDecks } from '@/hooks/usePersonalDecks'
import { resetDemoStore } from '../demoStore'
import { DemoModeProvider } from '../DemoModeProvider'

beforeEach(() => {
  localStorage.clear()
  resetDemoStore()
})

function Probe() {
  const { data } = usePersonalDecks()
  return <div data-testid="count">{data ? String(data.length) : 'loading'}</div>
}

describe('DemoModeProvider under Strict Mode', () => {
  it("keeps the fetch interceptor installed through Strict Mode's mount/cleanup/mount cycle", async () => {
    const realFetch = window.fetch

    render(
      <StrictMode>
        <MemoryRouter>
          <DemoModeProvider>
            <Probe />
          </DemoModeProvider>
        </MemoryRouter>
      </StrictMode>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('count').textContent).not.toBe('loading')
    })

    // Strict Mode (dev only) mounts effects, runs their cleanup, then mounts
    // them again — specifically to catch a setup/teardown pair where only
    // the first setup ever runs. If `installDemoFetch`'s cleanup fires
    // without anything re-installing it, `window.fetch` silently reverts to
    // the real fetch here, and every query fired after this point (e.g. a
    // tab switch remounting a section) goes out un-intercepted instead of
    // to the demo router.
    expect(window.fetch).not.toBe(realFetch)
  })
})
