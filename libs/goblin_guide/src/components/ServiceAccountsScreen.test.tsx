import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from '../auth/client'
import { IdentityProvider } from '../auth/IdentityProvider'
import { createMemoryTokenStore } from '../auth/tokenStore'
import type { ServiceAccount } from '../auth/schemas'
import { ServiceAccountsScreen } from './ServiceAccountsScreen'

const ADMIN = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'root@example.com',
  username: 'root',
  role: 'admin',
  is_active: true,
  is_verified: true,
  display_name: 'Root',
}

const ACTIVE: ServiceAccount = {
  id: '22222222-2222-4222-8222-222222222222',
  client_id: 'sa_3f9a2c7e8b1d4056',
  description: 'Tolaria News BFF cache warmer',
  scopes: ['bs:read', 'kt:read'],
  is_active: true,
  created_at: '2026-08-12T09:30:00Z',
}

const REVOKED: ServiceAccount = {
  id: '44444444-4444-4444-8444-444444444444',
  client_id: 'sa_a1b2c3d4e5f60718',
  description: 'One-off MTGJSON backfill',
  scopes: ['cards:write'],
  is_active: false,
  created_at: '2026-07-03T12:00:00Z',
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function makeFetch(seed: ServiceAccount[], principal: unknown = ADMIN) {
  let accounts = [...seed]
  const calls: { url: string; method: string; body: unknown }[] = []
  const fetchImpl: FetchLike = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const body = init?.body === undefined ? undefined : JSON.parse(String(init.body))
    calls.push({ url, method, body })

    if (url.endsWith('/auth/me')) return json(principal)

    if (url.endsWith('/api/v1/service-accounts') && method === 'GET') {
      return json(accounts)
    }
    if (url.endsWith('/api/v1/service-accounts') && method === 'POST') {
      const b = body as { description?: string | null; scopes: string[] }
      const account: ServiceAccount = {
        id: '99999999-9999-4999-8999-999999999999',
        client_id: 'sa_new0000000000000',
        description: b.description ?? null,
        scopes: b.scopes,
        is_active: true,
        created_at: '2026-08-30T12:00:00Z',
      }
      accounts = [...accounts, account]
      return json({ ...account, client_secret: 'plaintext-secret-shown-once' }, 201)
    }
    if (url.includes('/api/v1/service-accounts/') && url.endsWith('/revoke')) {
      const clientId = decodeURIComponent(
        url.slice(
          url.indexOf('/service-accounts/') + '/service-accounts/'.length,
          -'/revoke'.length,
        ),
      )
      accounts = accounts.map((a) =>
        a.client_id === clientId ? { ...a, is_active: false } : a,
      )
      return new Response(null, { status: 204 })
    }
    throw new Error(`unexpected ${method} ${url}`)
  })
  return { fetchImpl, calls }
}

function renderScreen(fetchImpl: FetchLike) {
  const store = createMemoryTokenStore()
  store.set({ access_token: 'a', refresh_token: 'r' })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const onBack = vi.fn()
  const ui: ReactElement = (
    <QueryClientProvider client={queryClient}>
      <IdentityProvider
        config={{ serviceUrl: 'https://identity.test', fetchImpl, tokenStore: store }}
      >
        <ServiceAccountsScreen onBack={onBack} />
      </IdentityProvider>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), onBack, ...render(ui) }
}

describe('<ServiceAccountsScreen>', () => {
  it('shows an access panel and never lists accounts for a non-admin', async () => {
    const { fetchImpl, calls } = makeFetch([ACTIVE], { ...ADMIN, role: 'user' })
    const { user, onBack } = renderScreen(fetchImpl)

    expect(
      await screen.findByRole('heading', { name: 'Administrator access required' }),
    ).toBeInTheDocument()
    expect(calls.some((c) => c.url.endsWith('/api/v1/service-accounts'))).toBe(false)

    await user.click(screen.getByRole('button', { name: 'Back to my account' }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('lists accounts, badging active vs revoked and only offering Revoke on active ones', async () => {
    const { fetchImpl } = makeFetch([ACTIVE, REVOKED])
    renderScreen(fetchImpl)

    expect(await screen.findByText('sa_3f9a2c7e8b1d4056')).toBeInTheDocument()
    expect(screen.getByText('sa_a1b2c3d4e5f60718')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('Revoked')).toBeInTheDocument()
    // One Revoke button — for the active account only.
    expect(screen.getAllByRole('button', { name: 'Revoke' })).toHaveLength(1)
  })

  it('shows the empty state when there are no accounts', async () => {
    const { fetchImpl } = makeFetch([])
    renderScreen(fetchImpl)

    expect(await screen.findByText(/No service accounts yet/)).toBeInTheDocument()
  })

  it('blocks a create with no scopes and sends no request', async () => {
    const { fetchImpl, calls } = makeFetch([])
    const { user } = renderScreen(fetchImpl)

    await user.click(
      await screen.findByRole('button', { name: 'Create service account' }),
    )

    expect(await screen.findByText('Add at least one scope.')).toBeInTheDocument()
    expect(
      calls.some(
        (c) => c.method === 'POST' && c.url.endsWith('/api/v1/service-accounts'),
      ),
    ).toBe(false)
  })

  it('creates an account, reveals the one-time secret, then returns to the list', async () => {
    const { fetchImpl, calls } = makeFetch([])
    const { user } = renderScreen(fetchImpl)

    await user.type(await screen.findByLabelText(/Description/), 'Nightly job')
    const scopes = screen.getByLabelText('Scopes')
    await user.type(scopes, 'bs:read{Enter}')
    await user.type(scopes, 'kt:read{Enter}')
    await user.click(screen.getByRole('button', { name: 'Create service account' }))

    expect(await screen.findByText('plaintext-secret-shown-once')).toBeInTheDocument()
    const post = calls.find(
      (c) => c.method === 'POST' && c.url.endsWith('/api/v1/service-accounts'),
    )
    expect(post?.body).toEqual({
      description: 'Nightly job',
      scopes: ['bs:read', 'kt:read'],
    })

    await user.click(screen.getByRole('button', { name: /Done/ }))
    expect(
      await screen.findByRole('heading', { name: 'New service account' }),
    ).toBeInTheDocument()
    expect(screen.getByText('sa_new0000000000000')).toBeInTheDocument()
  })

  it('walks a revoke from the list through the confirm screen', async () => {
    const { fetchImpl, calls } = makeFetch([ACTIVE])
    const { user } = renderScreen(fetchImpl)

    await user.click(await screen.findByRole('button', { name: 'Revoke' }))

    expect(
      await screen.findByRole('heading', { name: 'Revoke service account' }),
    ).toBeInTheDocument()

    // Cancel returns to the list unchanged.
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(
      await screen.findByRole('heading', { name: 'New service account' }),
    ).toBeInTheDocument()

    // Do it for real this time.
    await user.click(screen.getByRole('button', { name: 'Revoke' }))
    await user.click(screen.getByRole('button', { name: 'Revoke service account' }))

    await waitFor(() => {
      expect(
        calls.some(
          (c) =>
            c.method === 'POST' &&
            c.url.endsWith('/api/v1/service-accounts/sa_3f9a2c7e8b1d4056/revoke'),
        ),
      ).toBe(true)
    })
    expect(
      await screen.findByRole('heading', { name: 'New service account' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Revoke' })).not.toBeInTheDocument()
  })
})
