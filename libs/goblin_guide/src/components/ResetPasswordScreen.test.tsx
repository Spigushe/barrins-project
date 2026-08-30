import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from '../auth/client'
import { IdentityProvider } from '../auth/IdentityProvider'
import { ResetPasswordScreen, type ResetPasswordScreenProps } from './ResetPasswordScreen'

const PAIR = { access_token: 'a', refresh_token: 'r', token_type: 'bearer' }
const STRONG = 'GoblinGuide!23x'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function renderReset(props: ResetPasswordScreenProps, fetchImpl: FetchLike) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const ui: ReactElement = (
    <QueryClientProvider client={queryClient}>
      <IdentityProvider config={{ serviceUrl: 'https://identity.test', fetchImpl }}>
        <ResetPasswordScreen {...props} />
      </IdentityProvider>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), ...render(ui) }
}

describe('<ResetPasswordScreen>', () => {
  it('pre-fills email and code from the deep-link params (non-digits stripped)', () => {
    renderReset({ initialEmail: 'alex@example.com', initialCode: 'ab418203zz' }, vi.fn())
    expect(screen.getByLabelText('Email')).toHaveValue('alex@example.com')
    expect(screen.getByLabelText('Reset code')).toHaveValue('418203')
  })

  it('blocks a submit until the code is six digits and a password is set', async () => {
    const fetchImpl = vi.fn()
    const { user } = renderReset({ initialEmail: 'alex@example.com' }, fetchImpl)

    await user.type(screen.getByLabelText('Reset code'), '4182')
    await user.type(screen.getByLabelText('New password'), STRONG)
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter your email, the 6-digit code, and a new password.',
    )
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('confirms the reset and calls onAuthenticated', async () => {
    const onAuthenticated = vi.fn()
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe('https://identity.test/api/v1/auth/password-reset/confirm')
      expect(JSON.parse(String(init?.body))).toEqual({
        email: 'alex@example.com',
        code: '418203',
        new_password: STRONG,
      })
      return json(PAIR)
    })
    const { user } = renderReset(
      { initialEmail: 'alex@example.com', initialCode: '418203', onAuthenticated },
      fetchImpl,
    )

    await user.type(screen.getByLabelText('New password'), STRONG)
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    await waitFor(() => {
      expect(onAuthenticated).toHaveBeenCalledTimes(1)
    })
  })

  it('shows the single message for a wrong or expired code', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Invalid or expired code.' } }, 400),
    )
    const { user } = renderReset(
      { initialEmail: 'alex@example.com', initialCode: '000000' },
      fetchImpl,
    )

    await user.type(screen.getByLabelText('New password'), STRONG)
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid or expired code.')
  })

  it('tracks the typed password against the complexity checklist', async () => {
    const { user } = renderReset({ initialEmail: 'alex@example.com' }, vi.fn())

    const digitRule = screen.getByText('One digit').closest('.gg-rule')
    expect(digitRule).toHaveAttribute('data-met', 'false')

    await user.type(screen.getByLabelText('New password'), STRONG)

    expect(screen.getByText('One digit').closest('.gg-rule')).toHaveAttribute(
      'data-met',
      'true',
    )
  })
})
