import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { IdentityProvider } from '@barrins/goblin-guide'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { App } from './App'

const PAIR = { access_token: 'a', refresh_token: 'r', token_type: 'bearer' }
const PRINCIPAL = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'alex@example.com',
  username: 'alex_bishop',
  role: 'user',
  is_active: true,
  is_verified: true,
  display_name: 'Alex Bishop',
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

type FetchImpl = (url: string, init?: RequestInit) => Promise<Response>

function renderApp(path: string, fetchImpl: FetchImpl) {
  window.history.pushState({}, '', path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return {
    user: userEvent.setup(),
    ...render(
      <QueryClientProvider client={queryClient}>
        <IdentityProvider config={{ serviceUrl: 'https://identity.test', fetchImpl }}>
          <App />
        </IdentityProvider>
      </QueryClientProvider>,
    ),
  }
}

describe('<App>', () => {
  it('redirects an unauthenticated visit to / onto the login screen', async () => {
    renderApp('/', vi.fn())
    expect(
      await screen.findByRole('heading', { name: "Barrin's Identity" }),
    ).toBeInTheDocument()
  })

  it('shows the session-expired banner on /login?expired=1', async () => {
    renderApp('/login?expired=1', vi.fn())
    expect(await screen.findByRole('status')).toHaveTextContent('Your session has ended.')
  })

  it('signs in and lands on the account shell', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/token')) return jsonResponse(PAIR)
      if (url.endsWith('/auth/me')) return jsonResponse(PRINCIPAL)
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp('/login', fetchImpl)

    await user.type(screen.getByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter2hunter2')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(
      await screen.findByRole('heading', { name: 'You’re signed in' }),
    ).toBeInTheDocument()
    expect(screen.getByText('alex_bishop')).toBeInTheDocument()
  })
})
