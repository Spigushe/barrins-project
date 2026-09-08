import { afterEach, describe, expect, it, vi } from 'vitest'
import { searchCardsByNamePrefix } from '@/api/cards'

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('searchCardsByNamePrefix', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('queries the public prefix-search endpoint, excluding Duel-Commander-banned cards', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(['Thoughtseize']))
    vi.stubGlobal('fetch', fetchMock)

    const result = await searchCardsByNamePrefix('thou')

    expect(result).toEqual(['Thoughtseize'])
    const calledUrl = new URL(fetchMock.mock.calls[0][0] as string)
    expect(calledUrl.pathname).toBe('/api/v1/cards/search-by-name-prefix')
    expect(calledUrl.searchParams.get('q')).toBe('thou')
    expect(calledUrl.searchParams.get('exclude_banned_in')).toBe('duelcommander')
  })
})
