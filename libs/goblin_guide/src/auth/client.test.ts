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
