import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { ApiError, apiRequest } from '@/api/client'
import { clearSession, setSession } from '@/api/session'
import { setViewingOwner } from '@/api/viewingOwner'

const responseSchema = z.object({ ok: z.boolean() })

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

describe('apiRequest', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    clearSession()
    setViewingOwner(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('adds no owner_id on GET when no viewing owner is set', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/bff/tamiyo-scroll/personal-decks', responseSchema, {
      applyOwnerParam: true,
    })

    const calledUrl = new URL(fetchMock.mock.calls[0][0] as string)
    expect(calledUrl.searchParams.has('owner_id')).toBe(false)
  })

  it('injects owner_id on GET when a viewing owner is set and applyOwnerParam is true', async () => {
    setViewingOwner({ id: 'owner-123', label: 'Alice' })
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/bff/tamiyo-scroll/personal-decks', responseSchema, {
      applyOwnerParam: true,
    })

    const calledUrl = new URL(fetchMock.mock.calls[0][0] as string)
    expect(calledUrl.searchParams.get('owner_id')).toBe('owner-123')
  })

  it('never injects owner_id on a mutation even if applyOwnerParam were mistakenly set', async () => {
    setViewingOwner({ id: 'owner-123', label: 'Alice' })
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/bff/tamiyo-scroll/personal-decks', responseSchema, {
      method: 'POST',
      applyOwnerParam: true,
      body: { name: 'Deck' },
    })

    const calledUrl = new URL(fetchMock.mock.calls[0][0] as string)
    expect(calledUrl.searchParams.has('owner_id')).toBe(false)
  })

  it('attaches the Authorization header when a session exists', async () => {
    setSession({ access_token: 'access-abc', refresh_token: 'refresh-abc' })
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/bff/tamiyo-scroll/personal-decks', responseSchema)

    const requestInit = fetchMock.mock.calls[0][1] as RequestInit
    const headers = requestInit.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer access-abc')
  })

  it('refreshes once on 401 then retries the original request', async () => {
    setSession({ access_token: 'expired', refresh_token: 'refresh-abc' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: 'fresh',
          refresh_token: 'refresh-abc',
          token_type: 'bearer',
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiRequest('/bff/tamiyo-scroll/personal-decks', responseSchema)

    expect(result).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    const retryHeaders = fetchMock.mock.calls[2][1] as RequestInit
    const headers = retryHeaders.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer fresh')
  })

  it('clears the session and throws when the refresh call itself fails', async () => {
    setSession({ access_token: 'expired', refresh_token: 'bad-refresh' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
    vi.stubGlobal('fetch', fetchMock)
    vi.stubGlobal('location', { assign: vi.fn() })

    await expect(
      apiRequest('/bff/tamiyo-scroll/personal-decks', responseSchema),
    ).rejects.toThrow(ApiError)

    expect(localStorage.getItem('tamiyo_access_token')).toBeNull()
  })

  it('throws ApiError with the backend error envelope message', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(
          { error: { code: 'NOT_FOUND', message: 'Personal deck not found.' } },
          { status: 404 },
        ),
      )
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      apiRequest('/bff/tamiyo-scroll/personal-decks/xyz', responseSchema),
    ).rejects.toThrow('Personal deck not found.')
  })

  it('returns undefined for 204 responses without parsing the body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiRequest('/bff/tamiyo-scroll/personal-decks/xyz', z.void(), {
      method: 'DELETE',
    })
    expect(result).toBeUndefined()
  })
})
