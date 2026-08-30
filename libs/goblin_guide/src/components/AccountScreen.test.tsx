import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from '../auth/client'
import { IdentityProvider } from '../auth/IdentityProvider'
import { createMemoryTokenStore } from '../auth/tokenStore'
import { AccountScreen, type AccountScreenProps } from './AccountScreen'

const PRINCIPAL = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'alex@example.com',
  username: 'alex_bishop',
  role: 'user',
  is_active: true,
  is_verified: true,
  display_name: 'Alex Bishop',
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function renderAccount(props: AccountScreenProps, fetchImpl: FetchLike) {
  const store = createMemoryTokenStore()
  store.set({ access_token: 'a', refresh_token: 'r' })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const ui: ReactElement = (
    <QueryClientProvider client={queryClient}>
      <IdentityProvider
        config={{ serviceUrl: 'https://identity.test', fetchImpl, tokenStore: store }}
      >
        <AccountScreen {...props} />
      </IdentityProvider>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), store, ...render(ui) }
}

function patchBody(fetchImpl: ReturnType<typeof vi.fn>): unknown {
  const call = fetchImpl.mock.calls.find(
    (args) => (args[1] as RequestInit | undefined)?.method === 'PATCH',
  )
  return JSON.parse(String((call?.[1] as RequestInit | undefined)?.body))
}

describe('<AccountScreen>', () => {
  it('shows the profile and only enables Save once the display name changes', async () => {
    let principal = { ...PRINCIPAL }
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/auth/me')) return json(principal)
      if (url.endsWith('/users/me') && init?.method === 'PATCH') {
        principal = { ...principal, ...JSON.parse(String(init.body)) }
        return json(principal)
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderAccount({}, fetchImpl)

    const field = await screen.findByLabelText('Display name')
    expect(field).toHaveValue('Alex Bishop')
    expect(screen.getByText('alex_bishop')).toBeInTheDocument()

    const save = screen.getByRole('button', { name: 'Save display name' })
    expect(save).toBeDisabled()

    await user.clear(field)
    await user.type(field, 'Ajax')
    expect(save).toBeEnabled()
    await user.click(save)

    expect(await screen.findByText('Display name updated.')).toBeInTheDocument()
    expect(patchBody(fetchImpl)).toEqual({ display_name: 'Ajax' })
  })

  it('sends display_name: null when the field is cleared', async () => {
    let principal: Record<string, unknown> = { ...PRINCIPAL }
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/auth/me')) return json(principal)
      if (url.endsWith('/users/me') && init?.method === 'PATCH') {
        principal = { ...principal, display_name: null }
        return json(principal)
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderAccount({}, fetchImpl)

    const field = await screen.findByLabelText('Display name')
    await user.clear(field)
    await user.click(screen.getByRole('button', { name: 'Save display name' }))

    await waitFor(() => {
      expect(patchBody(fetchImpl)).toEqual({ display_name: null })
    })
  })

  it('walks an email change from address entry to confirmation', async () => {
    let principal = { ...PRINCIPAL }
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/auth/me')) return json(principal)
      if (url.endsWith('/users/me') && init?.method === 'PATCH') {
        expect(JSON.parse(String(init.body))).toEqual({ email: 'new@example.com' })
        return json(principal) // old address stays authoritative
      }
      if (url.endsWith('/email-change/verify') && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({ code: '123456' })
        principal = { ...principal, email: 'new@example.com' }
        return json(principal)
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderAccount({}, fetchImpl)

    await user.click(await screen.findByRole('button', { name: 'Change email' }))
    await user.type(screen.getByLabelText('New email'), 'new@example.com')
    await user.click(screen.getByRole('button', { name: 'Send confirmation code' }))

    // On the code step, the banner names the pending address.
    expect(await screen.findByText('new@example.com')).toBeInTheDocument()

    // A short code is rejected client-side.
    await user.type(screen.getByLabelText('Confirmation code'), '123')
    await user.click(screen.getByRole('button', { name: 'Confirm new email' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter the 6-digit code from your email.',
    )

    await user.type(screen.getByLabelText('Confirmation code'), '456')
    await user.click(screen.getByRole('button', { name: 'Confirm new email' }))

    expect(await screen.findByText('Email updated.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Change email' })).toBeInTheDocument()
  })

  it('opens on the code step from a deep link and resends with a cooldown', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/me')) return json(PRINCIPAL)
      if (url.endsWith('/email-change/resend')) {
        return json(
          { detail: 'A new code has been sent to the pending email address.' },
          202,
        )
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderAccount(
      { initialEmailChangeCode: 'zz123456', initialPendingEmail: 'new@example.com' },
      fetchImpl,
    )

    expect(await screen.findByLabelText('Confirmation code')).toHaveValue('123456')

    await user.click(screen.getByRole('button', { name: 'Resend code' }))

    expect(await screen.findByText(/a new code has been sent/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Resend code' })).not.toBeInTheDocument()
    expect(screen.getByText(/Resend available in \d+s/)).toBeInTheDocument()
  })

  it('deletes the account after re-entering the current password', async () => {
    const onDeleted = vi.fn()
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/auth/me')) return json(PRINCIPAL)
      if (url.endsWith('/auth/refresh')) {
        return json({ access_token: 'a2', refresh_token: 'r2', token_type: 'bearer' })
      }
      if (url.endsWith('/users/me') && init?.method === 'DELETE') {
        const body = JSON.parse(String(init.body)) as { current_password: string }
        if (body.current_password !== 'hunter2hunter2') {
          return json({ error: { message: 'Invalid password.' } }, 401)
        }
        return new Response(null, { status: 204 })
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user, store } = renderAccount({ onDeleted }, fetchImpl)

    await user.click(await screen.findByRole('button', { name: /Delete account/ }))

    await user.click(screen.getByRole('button', { name: 'Delete my account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter your current password.',
    )

    await user.type(screen.getByLabelText('Current password'), 'nope')
    await user.click(screen.getByRole('button', { name: 'Delete my account' }))
    expect(await screen.findByText('Invalid password.')).toBeInTheDocument()

    await user.clear(screen.getByLabelText('Current password'))
    await user.type(screen.getByLabelText('Current password'), 'hunter2hunter2')
    await user.click(screen.getByRole('button', { name: 'Delete my account' }))

    await waitFor(() => {
      expect(onDeleted).toHaveBeenCalledTimes(1)
    })
    expect(store.getAccess()).toBeNull()
  })
})
