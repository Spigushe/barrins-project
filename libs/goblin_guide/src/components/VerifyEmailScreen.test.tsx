import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from '../auth/client'
import { IdentityProvider } from '../auth/IdentityProvider'
import { VerifyEmailScreen, type VerifyEmailScreenProps } from './VerifyEmailScreen'

const PAIR = { access_token: 'a', refresh_token: 'r', token_type: 'bearer' }

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function renderVerify(props: VerifyEmailScreenProps, fetchImpl: FetchLike) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const ui: ReactElement = (
    <QueryClientProvider client={queryClient}>
      <IdentityProvider config={{ serviceUrl: 'https://identity.test', fetchImpl }}>
        <VerifyEmailScreen {...props} />
      </IdentityProvider>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), ...render(ui) }
}

describe('<VerifyEmailScreen>', () => {
  it('pre-fills email and code from the deep-link params', () => {
    renderVerify({ initialEmail: 'alex@example.com', initialCode: 'ab123456xx' }, vi.fn())
    expect(screen.getByLabelText('Email')).toHaveValue('alex@example.com')
    // non-digits stripped, capped at 6
    expect(screen.getByLabelText('Verification code')).toHaveValue('123456')
  })

  it('blocks a submit until the code is six digits', async () => {
    const fetchImpl = vi.fn()
    const { user } = renderVerify({ initialEmail: 'alex@example.com' }, fetchImpl)

    await user.type(screen.getByLabelText('Verification code'), '123')
    await user.click(screen.getByRole('button', { name: 'Verify email' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter your email and the 6-digit code.',
    )
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('calls onAuthenticated once the code is accepted', async () => {
    const onAuthenticated = vi.fn()
    const fetchImpl = vi.fn(async () => json(PAIR))
    const { user } = renderVerify(
      { initialEmail: 'alex@example.com', onAuthenticated },
      fetchImpl,
    )

    await user.type(screen.getByLabelText('Verification code'), '123456')
    await user.click(screen.getByRole('button', { name: 'Verify email' }))

    await waitFor(() => {
      expect(onAuthenticated).toHaveBeenCalledTimes(1)
    })
  })

  it('shows the server message for an invalid code', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Invalid or expired code.' } }, 400),
    )
    const { user } = renderVerify({ initialEmail: 'alex@example.com' }, fetchImpl)

    await user.type(screen.getByLabelText('Verification code'), '000000')
    await user.click(screen.getByRole('button', { name: 'Verify email' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid or expired code.')
  })

  it('resends a code and starts the cooldown', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/signup/resend')) {
        return json(
          { detail: 'If an account exists for this address, a new code has been sent.' },
          202,
        )
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderVerify({ initialEmail: 'alex@example.com' }, fetchImpl)

    await user.click(screen.getByRole('button', { name: 'Resend code' }))

    expect(await screen.findByText(/a new code has been sent/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Resend code' })).not.toBeInTheDocument()
    expect(screen.getByText(/Resend available in \d+s/)).toBeInTheDocument()
    expect(fetchImpl).toHaveBeenCalledTimes(1)
  })
})
