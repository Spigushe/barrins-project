import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createIdentityClient, IdentityError } from './client'
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
