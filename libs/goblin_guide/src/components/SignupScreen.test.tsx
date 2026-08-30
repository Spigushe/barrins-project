import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { FetchLike } from '../auth/client'
import { IdentityProvider } from '../auth/IdentityProvider'
import { SignupScreen, type SignupScreenProps } from './SignupScreen'

const PAIR = { access_token: 'a', refresh_token: 'r', token_type: 'bearer' }

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

function renderSignup(props: SignupScreenProps, fetchImpl: FetchLike) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const ui: ReactElement = (
    <QueryClientProvider client={queryClient}>
      <IdentityProvider config={{ serviceUrl: 'https://identity.test', fetchImpl }}>
        <SignupScreen {...props} />
      </IdentityProvider>
    </QueryClientProvider>
  )
  return { user: userEvent.setup(), ...render(ui) }
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Email'), 'alex@example.com')
  await user.type(screen.getByLabelText('Username'), 'alex_bishop')
  await user.type(screen.getByLabelText('Password'), 'GoblinGuide!23x')
}

describe('<SignupScreen>', () => {
  it('renders the account fields', () => {
    renderSignup({}, vi.fn())
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Display name')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create account' })).toBeEnabled()
  })

  it('blocks an empty submit with a client-side message and no request', async () => {
    const fetchImpl = vi.fn()
    const { user } = renderSignup({}, fetchImpl)

    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Email, username, and password are required.',
    )
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('reflects the typed password against the rule checklist', async () => {
    const { user } = renderSignup({}, vi.fn())

    await user.type(screen.getByLabelText('Password'), 'abc')
    expect(screen.getByText('One lowercase letter').closest('li')).toHaveAttribute(
      'data-met',
      'true',
    )
    expect(screen.getByText('One digit').closest('li')).toHaveAttribute(
      'data-met',
      'false',
    )

    await user.type(screen.getByLabelText('Password'), 'D3!efghijklmno')
    for (const label of [
      'At least 12 characters',
      'One uppercase letter',
      'One lowercase letter',
      'One digit',
      'One symbol',
    ]) {
      expect(screen.getByText(label).closest('li')).toHaveAttribute('data-met', 'true')
    }
  })

  it('routes to verification when the account needs an email check', async () => {
    const onVerificationRequired = vi.fn()
    const fetchImpl = vi.fn(async () =>
      json(
        { detail: 'check your inbox', verification_required: true, tokens: null },
        201,
      ),
    )
    const { user } = renderSignup({ onVerificationRequired }, fetchImpl)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() => {
      expect(onVerificationRequired).toHaveBeenCalledWith('alex@example.com')
    })
  })

  it('calls onAuthenticated when signup returns tokens directly', async () => {
    const onAuthenticated = vi.fn()
    const fetchImpl = vi.fn(async () =>
      json({ detail: 'created', verification_required: false, tokens: PAIR }, 201),
    )
    const { user } = renderSignup({ onAuthenticated }, fetchImpl)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() => {
      expect(onAuthenticated).toHaveBeenCalledTimes(1)
    })
  })

  it('surfaces the server message when the username is taken', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: "The username 'alex_bishop' is already taken." } }, 409),
    )
    const { user } = renderSignup({}, fetchImpl)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "The username 'alex_bishop' is already taken.",
    )
  })

  it('locks the form while the request is in flight', async () => {
    let release: (() => void) | undefined
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    const fetchImpl = vi.fn(async () => {
      await gate
      return json({ detail: 'ok', verification_required: true, tokens: null }, 201)
    })
    const { user } = renderSignup({}, fetchImpl)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    const button = await screen.findByRole('button', { name: 'Creating account…' })
    expect(button).toBeDisabled()
    expect(screen.getByLabelText('Email')).toBeDisabled()

    release?.()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Create account' })).toBeEnabled()
    })
  })
})
