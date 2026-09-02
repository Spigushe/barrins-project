import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from '../auth/client'
import { IdentityProvider } from '../auth/IdentityProvider'
import { LoginScreen, type LoginScreenProps } from './LoginScreen'

const PAIR = { access_token: 'a', refresh_token: 'r', token_type: 'bearer' }

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function renderLogin(props: LoginScreenProps, fetchImpl: FetchLike) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const ui: ReactElement = (
    <QueryClientProvider client={queryClient}>
      <IdentityProvider config={{ serviceUrl: 'https://identity.test', fetchImpl }}>
        <LoginScreen {...props} />
      </IdentityProvider>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), ...render(ui) }
}

describe('<LoginScreen>', () => {
  it('renders the wordmark and the two fields', () => {
    renderLogin({}, vi.fn())
    expect(screen.getByRole('heading', { name: "Barrin's Identity" })).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Log in' })).toBeEnabled()
  })

  it('shows the account-deleted banner when the prop is set', () => {
    renderLogin({ accountDeleted: true }, vi.fn())
    expect(screen.getByRole('status')).toHaveTextContent('Your account has been deleted.')
  })

  it('blocks an empty submit with a client-side message and no request', async () => {
    const fetchImpl = vi.fn()
    const { user } = renderLogin({}, fetchImpl)

    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Email and password are required.',
    )
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('calls onAuthenticated after a successful login', async () => {
    const onAuthenticated = vi.fn()
    const fetchImpl = vi.fn(async () => json(PAIR))
    const { user } = renderLogin({ onAuthenticated }, fetchImpl)

    await user.type(screen.getByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter2hunter2')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    await waitFor(() => {
      expect(onAuthenticated).toHaveBeenCalledTimes(1)
    })
  })

  it('surfaces the uniform 401 message from the service', async () => {
    const fetchImpl = vi.fn(async () => json({ detail: 'Invalid credentials.' }, 401))
    const { user } = renderLogin({}, fetchImpl)

    await user.type(screen.getByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrongpass1234')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials.')
  })

  it('shows the session-expired banner when asked', () => {
    renderLogin({ sessionExpired: true }, vi.fn())
    expect(screen.getByRole('status')).toHaveTextContent('Your session has ended.')
  })

  it('locks the form while the request is in flight', async () => {
    let release: (() => void) | undefined
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    const fetchImpl = vi.fn(async () => {
      await gate
      return json(PAIR)
    })
    const { user } = renderLogin({}, fetchImpl)

    await user.type(screen.getByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter2hunter2')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    const button = await screen.findByRole('button', { name: 'Signing in…' })
    expect(button).toBeDisabled()
    expect(screen.getByLabelText('Email')).toBeDisabled()

    release?.()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Log in' })).toBeEnabled()
    })
  })
})
