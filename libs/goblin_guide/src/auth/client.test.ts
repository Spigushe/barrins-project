import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createIdentityClient, type FetchLike, IdentityError } from './client'
import { createMemoryTokenStore, type TokenStore } from './tokenStore'

const SERVICE_URL = 'https://identity.test'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

const PAIR = {
  access_token: 'access-1',
  refresh_token: 'refresh-1',
  token_type: 'bearer',
}
const PAIR_2 = {
  access_token: 'access-2',
  refresh_token: 'refresh-2',
  token_type: 'bearer',
}
const PRINCIPAL = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'alex@example.com',
  username: 'alex_bishop',
  role: 'user',
  is_active: true,
  is_verified: true,
  display_name: 'Alex Bishop',
}

let store: TokenStore

beforeEach(() => {
  store = createMemoryTokenStore()
})

describe('login', () => {
  it('posts the email as the OAuth2 username field and stores the pair', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/token`)
      const body = init?.body as URLSearchParams
      expect(body.get('username')).toBe('alex@example.com')
      expect(body.get('password')).toBe('hunter2hunter2')
      return json(PAIR)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    const result = await client.login('alex@example.com', 'hunter2hunter2')

    expect(result.access_token).toBe('access-1')
    expect(store.getAccess()).toBe('access-1')
    expect(store.getRefresh()).toBe('refresh-1')
  })

  it('throws IdentityError with the parsed detail on 401 and stores nothing', async () => {
    const fetchImpl = vi.fn(async () => json({ detail: 'Invalid credentials.' }, 401))
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.login('x@example.com', 'nope')).rejects.toMatchObject({
      name: 'IdentityError',
      status: 401,
      message: 'Invalid credentials.',
    })
    expect(store.getAccess()).toBeNull()
  })
})

describe('me + silent refresh', () => {
  it('sends a bearer token and returns the principal', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/me`)
      expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer access-1')
      return json(PRINCIPAL)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.me()).resolves.toMatchObject({
      username: 'alex_bishop',
      role: 'user',
    })
  })

  it('refreshes once on a 401 and retries with the rotated token', async () => {
    store.set(PAIR)
    const calls: string[] = []
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(url)
      if (url.endsWith('/auth/me')) {
        const token = new Headers(init?.headers).get('Authorization')
        return token === 'Bearer access-2'
          ? json(PRINCIPAL)
          : json({ detail: 'expired' }, 401)
      }
      if (url.endsWith('/auth/refresh')) return json(PAIR_2)
      throw new Error(`unexpected ${url}`)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.me()).resolves.toMatchObject({ username: 'alex_bishop' })
    expect(calls.filter((u) => u.endsWith('/auth/refresh'))).toHaveLength(1)
    expect(store.getAccess()).toBe('access-2')
  })

  it('clears the store and throws when refresh also fails', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/refresh')) return json({ detail: 'nope' }, 401)
      return json({ detail: 'expired' }, 401)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.me()).rejects.toBeInstanceOf(IdentityError)
    expect(store.getAccess()).toBeNull()
    expect(store.getRefresh()).toBeNull()
  })

  it('throws without calling the network when there is no refresh token', async () => {
    store.set({ access_token: 'orphan', refresh_token: '' })
    // Force the refresh path: access present, but refresh token is empty.
    const emptyRefreshStore: TokenStore = { ...store, getRefresh: () => null }
    const fetchImpl = vi.fn(async () => json({ detail: 'expired' }, 401))
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: emptyRefreshStore,
      fetchImpl,
    })

    await expect(client.me()).rejects.toBeInstanceOf(IdentityError)
    expect(fetchImpl).toHaveBeenCalledTimes(1) // the /me call only, no /refresh
  })

  it('coalesces concurrent 401s into a single refresh', async () => {
    store.set(PAIR)
    let refreshCount = 0
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/auth/refresh')) {
        refreshCount += 1
        return json(PAIR_2)
      }
      const token = new Headers(init?.headers).get('Authorization')
      return token === 'Bearer access-2'
        ? json(PRINCIPAL)
        : json({ detail: 'expired' }, 401)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await Promise.all([client.me(), client.me(), client.me()])
    expect(refreshCount).toBe(1)
  })
})

describe('logout', () => {
  it('clears local token state even if the request rejects', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('network down')
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.logout()).resolves.toBeUndefined()
    expect(store.getAccess()).toBeNull()
  })
})

describe('signup', () => {
  it('posts JSON and returns the response when verification is required', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/signup`)
      expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
      expect(JSON.parse(String(init?.body))).toEqual({
        email: 'alex@example.com',
        username: 'alex_bishop',
        password: 'GoblinGuide!23x',
        display_name: 'Alex Bishop',
      })
      return json(
        {
          detail: 'Account created. Check your inbox to activate your account.',
          verification_required: true,
          tokens: null,
        },
        201,
      )
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    const result = await client.signup({
      email: 'alex@example.com',
      username: 'alex_bishop',
      password: 'GoblinGuide!23x',
      displayName: 'Alex Bishop',
    })

    expect(result.verification_required).toBe(true)
    expect(result.tokens).toBeNull()
    expect(store.getAccess()).toBeNull()
  })

  it('omits display_name when it is not provided', async () => {
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(JSON.parse(String(init?.body))).toEqual({
        email: 'alex@example.com',
        username: 'alex_bishop',
        password: 'GoblinGuide!23x',
      })
      return json({ detail: 'ok', verification_required: true, tokens: null }, 201)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await client.signup({
      email: 'alex@example.com',
      username: 'alex_bishop',
      password: 'GoblinGuide!23x',
    })
  })

  it('stores the pair when the server returns tokens (verification disabled)', async () => {
    const fetchImpl = vi.fn(async () =>
      json(
        { detail: 'Account created.', verification_required: false, tokens: PAIR },
        201,
      ),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    const result = await client.signup({
      email: 'alex@example.com',
      username: 'alex_bishop',
      password: 'GoblinGuide!23x',
    })

    expect(result.tokens).not.toBeNull()
    expect(store.getAccess()).toBe('access-1')
  })

  it('surfaces the { error: { message } } envelope on 409', async () => {
    const fetchImpl = vi.fn(async () =>
      json(
        {
          error: {
            code: 'CONFLICT',
            message: "The username 'alex_bishop' is already taken.",
          },
        },
        409,
      ),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(
      client.signup({
        email: 'alex@example.com',
        username: 'alex_bishop',
        password: 'GoblinGuide!23x',
      }),
    ).rejects.toMatchObject({
      name: 'IdentityError',
      status: 409,
      message: "The username 'alex_bishop' is already taken.",
    })
    expect(store.getAccess()).toBeNull()
  })

  it('throws IdentityError on a 422 validation failure', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Request validation failed' } }, 422),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(
      client.signup({ email: 'a@example.com', username: 'x', password: 'short' }),
    ).rejects.toBeInstanceOf(IdentityError)
  })
})

describe('verifyEmail', () => {
  it('posts the code and stores the returned pair', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/signup/verify`)
      expect(JSON.parse(String(init?.body))).toEqual({
        email: 'alex@example.com',
        code: '123456',
      })
      return json(PAIR)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await client.verifyEmail('alex@example.com', '123456')

    expect(store.getAccess()).toBe('access-1')
    expect(store.getRefresh()).toBe('refresh-1')
  })

  it('throws IdentityError with the message on 400', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Invalid or expired code.' } }, 400),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.verifyEmail('alex@example.com', '000000')).rejects.toMatchObject({
      status: 400,
      message: 'Invalid or expired code.',
    })
    expect(store.getAccess()).toBeNull()
  })
})

describe('resendVerification', () => {
  it('posts the email and returns the generic detail on 202', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/signup/resend`)
      expect(JSON.parse(String(init?.body))).toEqual({ email: 'alex@example.com' })
      return json(
        { detail: 'If an account exists for this address, a new code has been sent.' },
        202,
      )
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.resendVerification('alex@example.com')).resolves.toMatchObject({
      detail: 'If an account exists for this address, a new code has been sent.',
    })
  })

  it('throws IdentityError on a 502 send failure', async () => {
    const fetchImpl = vi.fn(async () =>
      json(
        {
          error: {
            message: 'Unable to send the verification email. Please try again later.',
          },
        },
        502,
      ),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.resendVerification('alex@example.com')).rejects.toBeInstanceOf(
      IdentityError,
    )
  })
})

describe('requestPasswordReset', () => {
  it('posts the email and returns the generic detail on 202', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/password-reset/request`)
      expect(JSON.parse(String(init?.body))).toEqual({ email: 'alex@example.com' })
      return json(
        { detail: 'If an account exists for this address, a reset code has been sent.' },
        202,
      )
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.requestPasswordReset('alex@example.com')).resolves.toMatchObject({
      detail: 'If an account exists for this address, a reset code has been sent.',
    })
  })

  it('throws IdentityError on a 502 send failure', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Unable to send the reset email.' } }, 502),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.requestPasswordReset('alex@example.com')).rejects.toBeInstanceOf(
      IdentityError,
    )
  })
})

describe('confirmPasswordReset', () => {
  it('posts email + code + new_password and stores the fresh pair', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/password-reset/confirm`)
      expect(JSON.parse(String(init?.body))).toEqual({
        email: 'alex@example.com',
        code: '123456',
        new_password: 'GoblinGuide!23x',
      })
      return json(PAIR)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await client.confirmPasswordReset('alex@example.com', '123456', 'GoblinGuide!23x')

    expect(store.getAccess()).toBe('access-1')
    expect(store.getRefresh()).toBe('refresh-1')
  })

  it('throws IdentityError with the single message on a 400 bad code and stores nothing', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Invalid or expired code.' } }, 400),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(
      client.confirmPasswordReset('alex@example.com', '000000', 'GoblinGuide!23x'),
    ).rejects.toMatchObject({ status: 400, message: 'Invalid or expired code.' })
    expect(store.getAccess()).toBeNull()
  })

  it('throws IdentityError on a 429 attempt cap', async () => {
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Too many attempts. Request a new code.' } }, 429),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(
      client.confirmPasswordReset('alex@example.com', '000000', 'GoblinGuide!23x'),
    ).rejects.toMatchObject({ status: 429 })
  })
})

describe('updateAccount', () => {
  it('PATCHes display_name with a bearer token and returns the principal', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/users/me`)
      expect(init?.method).toBe('PATCH')
      expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer access-1')
      expect(JSON.parse(String(init?.body))).toEqual({ display_name: 'Ajax' })
      return json({ ...PRINCIPAL, display_name: 'Ajax' })
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.updateAccount({ displayName: 'Ajax' })).resolves.toMatchObject({
      display_name: 'Ajax',
    })
  })

  it('sends display_name: null to clear it, and omits fields left undefined', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(JSON.parse(String(init?.body))).toEqual({ display_name: null })
      return json({ ...PRINCIPAL, display_name: null })
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await client.updateAccount({ displayName: null })
  })

  it('PATCHes a new email on its own; the response still shows the old address', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(JSON.parse(String(init?.body))).toEqual({ email: 'new@example.com' })
      return json(PRINCIPAL)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(
      client.updateAccount({ email: 'new@example.com' }),
    ).resolves.toMatchObject({ email: 'alex@example.com' })
  })

  it('throws IdentityError on a 409 when the new email is already registered', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async () =>
      json(
        { error: { message: "An account already exists for 'new@example.com'." } },
        409,
      ),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(
      client.updateAccount({ email: 'new@example.com' }),
    ).rejects.toMatchObject({ status: 409 })
  })
})

describe('verifyEmailChange', () => {
  it('posts just the code and returns the principal with the new email', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/users/me/email-change/verify`)
      expect(JSON.parse(String(init?.body))).toEqual({ code: '123456' })
      return json({ ...PRINCIPAL, email: 'new@example.com' })
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.verifyEmailChange('123456')).resolves.toMatchObject({
      email: 'new@example.com',
    })
  })

  it('throws IdentityError with the message on a 400 bad code', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'Invalid or expired code.' } }, 400),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.verifyEmailChange('000000')).rejects.toMatchObject({
      status: 400,
      message: 'Invalid or expired code.',
    })
  })
})

describe('resendEmailChange', () => {
  it('posts with no body and returns the detail on 202', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/users/me/email-change/resend`)
      expect(init?.method).toBe('POST')
      expect(init?.body).toBeUndefined()
      return json(
        { detail: 'A new code has been sent to the pending email address.' },
        202,
      )
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.resendEmailChange()).resolves.toMatchObject({
      detail: 'A new code has been sent to the pending email address.',
    })
  })

  it('throws IdentityError on a 404 when there is no pending change', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async () =>
      json({ error: { message: 'No pending email change.' } }, 404),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.resendEmailChange()).rejects.toMatchObject({ status: 404 })
  })
})

describe('deleteAccount', () => {
  it('sends the current password and clears the token store on 204', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/users/me`)
      expect(init?.method).toBe('DELETE')
      expect(JSON.parse(String(init?.body))).toEqual({
        current_password: 'hunter2hunter2',
      })
      return new Response(null, { status: 204 })
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.deleteAccount('hunter2hunter2')).resolves.toBeUndefined()
    expect(store.getAccess()).toBeNull()
    expect(store.getRefresh()).toBeNull()
  })

  it('surfaces a wrong-password 401 (after the silent-refresh retry) and keeps a session', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/refresh')) return json(PAIR_2)
      // Both the first DELETE and the post-refresh retry answer 401 — the
      // password is wrong, not the token.
      return json({ error: { message: 'Invalid password.' } }, 401)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.deleteAccount('nope')).rejects.toMatchObject({
      status: 401,
      message: 'Invalid password.',
    })
    expect(store.getAccess()).toBe('access-2')
  })
})

describe('service accounts', () => {
  const ACCOUNT = {
    id: '22222222-2222-4222-8222-222222222222',
    client_id: 'sa_3f9a2c7e8b1d4056',
    description: 'Tolaria News BFF cache warmer',
    scopes: ['bs:read', 'kt:read'],
    is_active: true,
    created_at: '2026-08-12T09:30:00Z',
  }

  it('lists accounts with a bearer token and parses the array', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/service-accounts`)
      expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer access-1')
      return json([
        ACCOUNT,
        {
          ...ACCOUNT,
          id: '33333333-3333-4333-8333-333333333333',
          client_id: 'sa_x',
          is_active: false,
        },
      ])
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.listServiceAccounts()).resolves.toHaveLength(2)
  })

  it('creates an account, sending description + scopes, and returns the one-time secret', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/service-accounts`)
      expect(init?.method).toBe('POST')
      expect(JSON.parse(String(init?.body))).toEqual({
        description: 'Nightly job',
        scopes: ['bs:read'],
      })
      return json({ ...ACCOUNT, client_secret: 'plaintext-secret-shown-once' }, 201)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(
      client.createServiceAccount({ description: 'Nightly job', scopes: ['bs:read'] }),
    ).resolves.toMatchObject({ client_secret: 'plaintext-secret-shown-once' })
  })

  it('omits description from the body when it is undefined', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(JSON.parse(String(init?.body))).toEqual({ scopes: ['bs:read'] })
      return json({ ...ACCOUNT, client_secret: 's' }, 201)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await client.createServiceAccount({ scopes: ['bs:read'] })
  })

  it('revokes by client_id and resolves on the 204', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(
        `${SERVICE_URL}/api/v1/service-accounts/sa_3f9a2c7e8b1d4056/revoke`,
      )
      expect(init?.method).toBe('POST')
      return new Response(null, { status: 204 })
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(
      client.revokeServiceAccount('sa_3f9a2c7e8b1d4056'),
    ).resolves.toBeUndefined()
  })

  it('throws IdentityError on a 404 for an unknown client_id', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async () =>
      json({ detail: "No service account found for client_id 'sa_nope'." }, 404),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.revokeServiceAccount('sa_nope')).rejects.toMatchObject({
      name: 'IdentityError',
      status: 404,
    })
  })

  it('surfaces a 403 for a non-admin caller', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async () =>
      json({ detail: 'The user does not have the required role.' }, 403),
    )
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.listServiceAccounts()).rejects.toMatchObject({ status: 403 })
  })
})

describe('listApplications', () => {
  const APP = {
    key: 'tamiyo_scroll',
    name: 'Tamiyo Scroll',
    description: 'Decks.',
    url: 'https://tamiyo.test',
    logo_svg: '<svg/>',
    access: 'open',
    min_role: null,
  }

  it('GETs the directory without a token when signed out and parses it', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/applications`)
      expect(new Headers(init?.headers).get('Authorization')).toBeNull()
      return json([APP])
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.listApplications()).resolves.toEqual([APP])
  })

  it('sends the bearer token when there is a session', async () => {
    store.set(PAIR)
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer access-1')
      return json([{ ...APP, access: 'role_denied', min_role: 'ml_developer' }])
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    const [row] = await client.listApplications()
    expect(row.access).toBe('role_denied')
  })

  it('throws IdentityError on a non-ok response', async () => {
    const fetchImpl = vi.fn(async () => json({ detail: 'nope' }, 500))
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await expect(client.listApplications()).rejects.toBeInstanceOf(IdentityError)
  })
})

describe('cookie mode (ADR-18)', () => {
  const cookieClient = (fetchImpl: FetchLike) =>
    createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
      cookieMode: true,
    })

  it('login sends X-Client: web + credentials and stores only the access token', async () => {
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/token`)
      expect(new Headers(init?.headers).get('X-Client')).toBe('web')
      expect(init?.credentials).toBe('include')
      // Identity omits the refresh token from the body in cookie mode.
      return json({ access_token: 'access-1', token_type: 'bearer' })
    })

    await cookieClient(fetchImpl).login('alex@example.com', 'hunter2hunter2')

    expect(store.getAccess()).toBe('access-1')
    expect(store.getRefresh()).toBeNull()
  })

  it('refresh posts no body, relies on the cookie, and rotates the access token', async () => {
    store.set({ access_token: 'access-1' })
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/refresh`)
      expect(init?.method).toBe('POST')
      expect(init?.body).toBeUndefined()
      expect(init?.credentials).toBe('include')
      expect(new Headers(init?.headers).get('X-Client')).toBe('web')
      return json({ access_token: 'access-2', token_type: 'bearer' })
    })

    const pair = await cookieClient(fetchImpl).refresh()

    expect(pair.access_token).toBe('access-2')
    expect(pair.refresh_token).toBeUndefined()
    expect(store.getAccess()).toBe('access-2')
  })

  it('me silently refreshes via the cookie on a 401 and retries once', async () => {
    store.set({ access_token: 'access-1' })
    const calls: string[] = []
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(url)
      if (url.endsWith('/auth/refresh')) {
        expect(init?.body).toBeUndefined()
        return json({ access_token: 'access-2', token_type: 'bearer' })
      }
      const token = new Headers(init?.headers).get('Authorization')
      return token === 'Bearer access-2'
        ? json(PRINCIPAL)
        : json({ detail: 'expired' }, 401)
    })

    await expect(cookieClient(fetchImpl).me()).resolves.toMatchObject({
      username: 'alex_bishop',
    })
    expect(calls.filter((u) => u.endsWith('/auth/refresh'))).toHaveLength(1)
    expect(store.getAccess()).toBe('access-2')
  })

  it('clears local state and throws when the cookie refresh is rejected', async () => {
    store.set({ access_token: 'access-1' })
    const fetchImpl = vi.fn(async (url: string) =>
      url.endsWith('/auth/refresh')
        ? json({ detail: 'nope' }, 401)
        : json({ detail: 'expired' }, 401),
    )

    await expect(cookieClient(fetchImpl).me()).rejects.toBeInstanceOf(IdentityError)
    expect(store.getAccess()).toBeNull()
  })

  it('logout sends credentials and clears local state', async () => {
    store.set({ access_token: 'access-1' })
    const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe(`${SERVICE_URL}/api/v1/auth/logout`)
      expect(init?.credentials).toBe('include')
      return new Response(null, { status: 204 })
    })

    await cookieClient(fetchImpl).logout()

    expect(store.getAccess()).toBeNull()
  })

  it('signup without verification stores only the access token', async () => {
    const fetchImpl = vi.fn(async () =>
      json(
        {
          detail: 'Account created.',
          verification_required: false,
          tokens: { access_token: 'access-1', token_type: 'bearer' },
        },
        201,
      ),
    )

    await cookieClient(fetchImpl).signup({
      email: 'alex@example.com',
      username: 'alex_bishop',
      password: 'GoblinGuide!23x',
    })

    expect(store.getAccess()).toBe('access-1')
    expect(store.getRefresh()).toBeNull()
  })
})

describe('body mode (default)', () => {
  it('sends neither the opt-in header nor credentials, and keeps the body refresh token', async () => {
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(new Headers(init?.headers).get('X-Client')).toBeNull()
      expect(init?.credentials).toBeUndefined()
      return json(PAIR)
    })
    const client = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: store,
      fetchImpl,
    })

    await client.login('alex@example.com', 'hunter2hunter2')

    expect(store.getRefresh()).toBe('refresh-1')
  })
})

describe('readDetail envelope', () => {
  it('prefers error.message and falls back to a bare detail', async () => {
    const withEnvelope = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: createMemoryTokenStore(),
      fetchImpl: vi.fn(async () => json({ error: { message: 'X' }, detail: 'Y' }, 400)),
    })
    await expect(
      withEnvelope.verifyEmail('a@example.com', '000000'),
    ).rejects.toMatchObject({ message: 'X' })

    const bareDetail = createIdentityClient({
      serviceUrl: SERVICE_URL,
      tokenStore: createMemoryTokenStore(),
      fetchImpl: vi.fn(async () => json({ detail: 'Y' }, 400)),
    })
    await expect(bareDetail.verifyEmail('a@example.com', '000000')).rejects.toMatchObject(
      { message: 'Y' },
    )
  })
})
