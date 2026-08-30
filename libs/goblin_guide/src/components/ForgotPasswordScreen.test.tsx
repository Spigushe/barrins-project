import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from '../auth/client'
import { IdentityProvider } from '../auth/IdentityProvider'
import {
  ForgotPasswordScreen,
  type ForgotPasswordScreenProps,
} from './ForgotPasswordScreen'

const GENERIC = 'If an account exists for this address, a reset code has been sent.'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function renderForgot(props: ForgotPasswordScreenProps, fetchImpl: FetchLike) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const ui: ReactElement = (
    <QueryClientProvider client={queryClient}>
      <IdentityProvider config={{ serviceUrl: 'https://identity.test', fetchImpl }}>
        <ForgotPasswordScreen {...props} />
      </IdentityProvider>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), ...render(ui) }
}

describe('<ForgotPasswordScreen>', () => {
  it('blocks a submit with no email and sends no request', async () => {
    const fetchImpl = vi.fn()
    const { user } = renderForgot({}, fetchImpl)

    await user.click(screen.getByRole('button', { name: 'Send reset code' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter your email address.',
    )
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('shows the generic confirmation after a request and offers the reset step', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      expect(url).toBe('https://identity.test/api/v1/auth/password-reset/request')
      return json({ detail: GENERIC }, 202)
    })
    const { user } = renderForgot({ initialEmail: 'alex@example.com' }, fetchImpl)

    await user.click(screen.getByRole('button', { name: 'Send reset code' }))

    expect(await screen.findByText(GENERIC)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Enter reset code' })).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Send reset code' }),
    ).not.toBeInTheDocument()
  })

  it('calls onEnterCode with the email from the confirmation step', async () => {
    const onEnterCode = vi.fn()
    const fetchImpl = vi.fn(async () => json({ detail: GENERIC }, 202))
    const { user } = renderForgot(
      { initialEmail: 'alex@example.com', onEnterCode },
      fetchImpl,
    )

    await user.click(screen.getByRole('button', { name: 'Send reset code' }))
    await user.click(await screen.findByRole('button', { name: 'Enter reset code' }))

    expect(onEnterCode).toHaveBeenCalledWith('alex@example.com')
  })

  it('surfaces a server error in an alert', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Too many requests. Try again later.' } }, 429),
    )
    const { user } = renderForgot({ initialEmail: 'alex@example.com' }, fetchImpl)

    await user.click(screen.getByRole('button', { name: 'Send reset code' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Too many requests. Try again later.',
    )
  })

  it('re-requests a code from the "Send again" link', async () => {
    const fetchImpl = vi.fn(async () => json({ detail: GENERIC }, 202))
    const { user } = renderForgot({ initialEmail: 'alex@example.com' }, fetchImpl)

    await user.click(screen.getByRole('button', { name: 'Send reset code' }))
    await user.click(await screen.findByRole('button', { name: 'Send again' }))

    await waitFor(() => {
      expect(fetchImpl).toHaveBeenCalledTimes(2)
    })
  })
})
