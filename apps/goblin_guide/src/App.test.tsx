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

function renderApp(path: string, fetchImpl: FetchImpl, cookieMode = false) {
  window.history.pushState({}, '', path)
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  // The home page now renders the app directory (ADR-19) alongside the
  // account screen; tests that don't care about it get an empty list.
  const withApps: FetchImpl = async (url, init) => {
    try {
      return await fetchImpl(url, init)
    } catch (err) {
      if (url.endsWith('/api/v1/applications')) return jsonResponse([])
      throw err
    }
  }
  return {
    user: userEvent.setup(),
    ...render(
      <QueryClientProvider client={queryClient}>
        <IdentityProvider
          config={{
            serviceUrl: 'https://identity.test',
            fetchImpl: withApps,
            cookieMode,
          }}
        >
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

  it('restores a cookie-mode session from the refresh cookie on a fresh load of /', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/api/v1/auth/refresh')) {
        expect(init?.credentials).toBe('include')
        return jsonResponse({ access_token: 'a', token_type: 'bearer' })
      }
      if (url.endsWith('/auth/me')) return jsonResponse(PRINCIPAL)
      throw new Error(`unexpected ${url}`)
    })
    renderApp('/', fetchImpl, true)

    // No login interaction — the session comes straight back from the cookie.
    expect(await screen.findByRole('heading', { name: 'Account' })).toBeInTheDocument()
    expect(screen.getByText('alex_bishop')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/')
  })

  it('sends a cookie-mode visitor with no session to the login screen', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/api/v1/auth/refresh')) return jsonResponse({ detail: 'no' }, 401)
      throw new Error(`unexpected ${url}`)
    })
    renderApp('/', fetchImpl, true)

    expect(
      await screen.findByRole('heading', { name: "Barrin's Identity" }),
    ).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
  })

  it('shows the session-expired banner on /login?expired=1', async () => {
    renderApp('/login?expired=1', vi.fn())
    expect(await screen.findByRole('status')).toHaveTextContent('Your session has ended.')
  })

  it('shows the account-deleted banner on /login?deleted=1', async () => {
    renderApp('/login?deleted=1', vi.fn())
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Your account has been deleted.',
    )
  })

  it('bounces an unauthenticated /confirm-email-change to the login screen', async () => {
    renderApp('/confirm-email-change?email=new@example.com&code=123456', vi.fn())
    expect(
      await screen.findByRole('heading', { name: "Barrin's Identity" }),
    ).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
    expect(window.location.search).toContain('next=')
  })

  it('bounces an unauthenticated /service-accounts to the login screen with ?next=', async () => {
    renderApp('/service-accounts', vi.fn())
    expect(
      await screen.findByRole('heading', { name: "Barrin's Identity" }),
    ).toBeInTheDocument()
    expect(window.location.pathname).toBe('/login')
    expect(window.location.search).toContain('next=%2Fservice-accounts')
  })

  it('shows the admin service-accounts screen to an admin and the access panel to others', async () => {
    const admin = { ...PRINCIPAL, role: 'admin' }
    const adminFetch = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/auth/token')) return jsonResponse(PAIR)
      if (url.endsWith('/auth/me')) return jsonResponse(admin)
      if (url.endsWith('/api/v1/service-accounts') && (init?.method ?? 'GET') === 'GET') {
        return jsonResponse([])
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp('/login?next=/service-accounts', adminFetch)

    await user.type(screen.getByLabelText('Email'), 'root@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter2hunter2')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(
      await screen.findByRole('heading', { name: 'New service account' }),
    ).toBeInTheDocument()
    // Admin header offers the toggle back to the account screen.
    expect(screen.getByRole('link', { name: 'Account' })).toBeInTheDocument()
  })

  it('shows the access panel on /service-accounts for a non-admin', async () => {
    const nonAdminFetch = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/token')) return jsonResponse(PAIR)
      if (url.endsWith('/auth/me')) return jsonResponse(PRINCIPAL)
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp('/login?next=/service-accounts', nonAdminFetch)

    await user.type(screen.getByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter2hunter2')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(
      await screen.findByRole('heading', { name: 'Administrator access required' }),
    ).toBeInTheDocument()
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

    expect(await screen.findByRole('heading', { name: 'Account' })).toBeInTheDocument()
    expect(screen.getByText('alex_bishop')).toBeInTheDocument()
  })

  it('signs in in cookie mode: opt-in header + credentials, no body refresh token', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/auth/token')) {
        expect(new Headers(init?.headers).get('X-Client')).toBe('web')
        expect(init?.credentials).toBe('include')
        // Identity keeps the refresh token in the HttpOnly cookie (ADR-18).
        return jsonResponse({ access_token: 'a', token_type: 'bearer' })
      }
      if (url.endsWith('/auth/me')) {
        expect(init?.credentials).toBe('include')
        return jsonResponse(PRINCIPAL)
      }
      // Fresh load with no cookie: the on-mount restore attempt (ADR-18)
      // comes back 401 and the login form takes over.
      if (url.endsWith('/api/v1/auth/refresh')) return jsonResponse({ detail: 'no' }, 401)
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp('/login', fetchImpl, true)

    await user.type(await screen.findByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter2hunter2')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('heading', { name: 'Account' })).toBeInTheDocument()
    expect(screen.getByText('alex_bishop')).toBeInTheDocument()
  })

  it('shows the app directory as the home second column, without Goblin Guide itself', async () => {
    const apps = [
      {
        key: 'goblin_guide',
        name: 'Goblin Guide',
        description: 'Account.',
        url: 'https://goblin.test',
        logo_svg: '<svg/>',
        access: 'open',
        min_role: null,
      },
      {
        key: 'tamiyo_scroll',
        name: 'Tamiyo Scroll',
        description: 'Decks.',
        url: 'https://tamiyo.test',
        logo_svg: '<svg/>',
        access: 'open',
        min_role: null,
      },
      {
        key: 'karn_jupyter',
        name: 'Karn Tablets',
        description: 'ML.',
        url: 'https://karn.test',
        logo_svg: '<svg/>',
        access: 'role_denied',
        min_role: 'ml_developer',
      },
    ]
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/token')) return jsonResponse(PAIR)
      if (url.endsWith('/auth/me')) return jsonResponse(PRINCIPAL)
      if (url.endsWith('/api/v1/applications')) return jsonResponse(apps)
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp('/login', fetchImpl)

    await user.type(screen.getByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter2hunter2')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    // Account column and directory column both on the home page.
    expect(await screen.findByRole('heading', { name: 'Account' })).toBeInTheDocument()
    expect(
      await screen.findByRole('heading', { name: 'Barrin’s applications' }),
    ).toBeInTheDocument()
    expect(await screen.findByText('Tamiyo Scroll')).toBeInTheDocument()
    expect(screen.getByText('Needs ml_developer')).toBeInTheDocument()
    expect(screen.queryByText('Goblin Guide')).not.toBeInTheDocument()
  })

  it('opens the signup screen from the login link', async () => {
    const { user } = renderApp('/login', vi.fn())

    await user.click(screen.getByRole('button', { name: 'Create an account' }))

    expect(
      await screen.findByRole('button', { name: 'Create account' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
  })

  it('takes a new signup to the verification screen with the email carried over', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/signup')) {
        return jsonResponse(
          { detail: 'check your inbox', verification_required: true, tokens: null },
          201,
        )
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp('/signup', fetchImpl)

    await user.type(screen.getByLabelText('Email'), 'alex@example.com')
    await user.type(screen.getByLabelText('Username'), 'alex_bishop')
    await user.type(screen.getByLabelText('Password'), 'GoblinGuide!23x')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(
      await screen.findByRole('button', { name: 'Verify email' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveValue('alex@example.com')
  })

  it('pre-fills the verification screen from a deep link and signs in on success', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/signup/verify')) return jsonResponse(PAIR)
      if (url.endsWith('/auth/me')) return jsonResponse(PRINCIPAL)
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp(
      '/verify-email?email=alex@example.com&code=123456',
      fetchImpl,
    )

    expect(screen.getByLabelText('Verification code')).toHaveValue('123456')
    await user.click(screen.getByRole('button', { name: 'Verify email' }))

    expect(await screen.findByRole('heading', { name: 'Account' })).toBeInTheDocument()
  })

  it('opens the forgot-password screen from the login link', async () => {
    const { user } = renderApp('/login', vi.fn())

    await user.click(screen.getByRole('button', { name: 'Forgot password?' }))

    expect(
      await screen.findByRole('button', { name: 'Send reset code' }),
    ).toBeInTheDocument()
  })

  it('requests a reset code then carries the email to the reset screen', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/password-reset/request')) {
        return jsonResponse(
          { detail: 'If an account exists, a code has been sent.' },
          202,
        )
      }
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp('/forgot-password', fetchImpl)

    await user.type(screen.getByLabelText('Email'), 'alex@example.com')
    await user.click(screen.getByRole('button', { name: 'Send reset code' }))

    await user.click(await screen.findByRole('button', { name: 'Enter reset code' }))

    expect(
      await screen.findByRole('button', { name: 'Reset password' }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveValue('alex@example.com')
  })

  it('pre-fills the reset screen from a deep link and signs in on success', async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/password-reset/confirm')) return jsonResponse(PAIR)
      if (url.endsWith('/auth/me')) return jsonResponse(PRINCIPAL)
      throw new Error(`unexpected ${url}`)
    })
    const { user } = renderApp(
      '/reset-password?email=alex@example.com&code=418203',
      fetchImpl,
    )

    expect(screen.getByLabelText('Reset code')).toHaveValue('418203')
    await user.type(screen.getByLabelText('New password'), 'GoblinGuide!23x')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    expect(await screen.findByRole('heading', { name: 'Account' })).toBeInTheDocument()
  })
})

describe('<App> — return_to back link', () => {
  const cookieRestore = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/api/v1/auth/refresh')) {
      expect(init?.credentials).toBe('include')
      return jsonResponse({ access_token: 'a', token_type: 'bearer' })
    }
    if (url.endsWith('/auth/me')) return jsonResponse(PRINCIPAL)
    throw new Error(`unexpected ${url}`)
  })

  it('offers a "Back to <label>" link on the account screen when return_to is set', async () => {
    renderApp(
      '/?return_to=https%3A%2F%2Ftamiyo.example.test%2F&return_label=Tamiyo%20Scroll',
      cookieRestore,
      true,
    )
    const back = await screen.findByRole('link', { name: '← Back to Tamiyo Scroll' })
    expect(back).toHaveAttribute('href', 'https://tamiyo.example.test/')
  })

  it('shows no back link without return_to', async () => {
    renderApp('/', cookieRestore, true)
    await screen.findByRole('heading', { name: 'Account' })
    expect(screen.queryByRole('link', { name: /^← Back to/ })).not.toBeInTheDocument()
  })

  it('ignores a non-http(s) return_to (no open redirect)', async () => {
    renderApp('/?return_to=javascript%3Aalert(1)&return_label=Evil', cookieRestore, true)
    await screen.findByRole('heading', { name: 'Account' })
    expect(screen.queryByRole('link', { name: /^← Back to/ })).not.toBeInTheDocument()
  })
})
