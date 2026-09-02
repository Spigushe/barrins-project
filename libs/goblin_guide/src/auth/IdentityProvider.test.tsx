import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from './client'
import { useIdentity } from './hooks'
import { IdentityProvider } from './IdentityProvider'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function Probe() {
  const { isAuthenticated, isBootstrapping } = useIdentity()
  return (
    <div>
      <span data-testid="authed">{String(isAuthenticated)}</span>
      <span data-testid="bootstrapping">{String(isBootstrapping)}</span>
    </div>
  )
}

function renderProvider(fetchImpl: FetchLike, cookieMode: boolean): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <IdentityProvider
        config={{ serviceUrl: 'https://identity.test', fetchImpl, cookieMode }}
      >
        <Probe />
      </IdentityProvider>
    </QueryClientProvider>,
  )
}

describe('<IdentityProvider> cookie-mode session restore (ADR-18)', () => {
  it('restores a session from the refresh cookie on mount', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/api/v1/auth/refresh')) {
        expect(init?.method).toBe('POST')
        expect(init?.credentials).toBe('include')
        expect(new Headers(init?.headers).get('X-Client')).toBe('web')
        // Refresh token stays in the HttpOnly cookie — body carries only access.
        return json({ access_token: 'restored', token_type: 'bearer' })
      }
      throw new Error(`unexpected ${url}`)
    })

    renderProvider(fetchImpl, true)

    // Loading state is up first, then the session comes back.
    expect(screen.getByTestId('bootstrapping')).toHaveTextContent('true')
    await waitFor(() =>
      expect(screen.getByTestId('bootstrapping')).toHaveTextContent('false'),
    )
    expect(screen.getByTestId('authed')).toHaveTextContent('true')
    expect(fetchImpl).toHaveBeenCalledTimes(1)
  })

  it('lands signed out when there is no valid refresh cookie', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/api/v1/auth/refresh')) return json({ detail: 'no' }, 401)
      throw new Error(`unexpected ${url}`)
    })

    renderProvider(fetchImpl, true)

    await waitFor(() =>
      expect(screen.getByTestId('bootstrapping')).toHaveTextContent('false'),
    )
    expect(screen.getByTestId('authed')).toHaveTextContent('false')
  })

  it('does not touch the network in body mode', async () => {
    const fetchImpl = vi.fn()
    renderProvider(fetchImpl as unknown as FetchLike, false)

    expect(screen.getByTestId('bootstrapping')).toHaveTextContent('false')
    expect(screen.getByTestId('authed')).toHaveTextContent('false')
    // Give any stray effect a chance to fire before asserting no calls.
    await Promise.resolve()
    expect(fetchImpl).not.toHaveBeenCalled()
  })
})
