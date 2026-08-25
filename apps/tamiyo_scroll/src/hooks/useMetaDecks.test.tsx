import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as metaDecksApi from '@/api/metaDecks'
import { useArchiveMetaDeck, useCreateMetaDeck, useUpdateMetaDeck } from './useMetaDecks'

vi.mock('@/api/metaDecks')

/**
 * F10 UAT regression: build_merged_view (sharing_merge.py) remaps a
 * sharer's opponent_deck_id to the viewer's own roster entry the moment a
 * same-named own entry exists (or stops existing on archive/rename). That
 * remap is recomputed fresh on every /matches fetch, so a stale cached
 * matches query — one fetched before the roster change — keeps pointing at
 * an opponent id the fresh /meta-decks list no longer has, and the match
 * log falls back to "?" (resolveMetaDeckOption finds nothing). Every
 * mutation that can shift the remap must therefore invalidate ['matches']
 * alongside ['meta-decks'].
 */
describe('useMetaDecks invalidation', () => {
  function wrapper(queryClient: QueryClient) {
    return function Wrapper({ children }: { children: ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    }
  }

  function seedMatchesQuery(queryClient: QueryClient) {
    const key = ['matches', 'self', 'deck-1']
    queryClient.setQueryData(key, [])
    return key
  }

  it('invalidates matches when a meta deck is created', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const matchesKey = seedMatchesQuery(queryClient)
    vi.mocked(metaDecksApi.createMetaDeck).mockResolvedValue({
      id: 'md-1',
      name: 'Aragorn, King of Gondor',
      tier: 'A',
      archetype: null,
      is_readonly: false,
      has_shared_data: false,
      merged_ids: ['md-1'],
    } as never)

    const { result } = renderHook(() => useCreateMetaDeck(), { wrapper: wrapper(queryClient) })
    await result.current.mutateAsync({ name: 'Aragorn, King of Gondor', personal_deck_id: 'deck-1' } as never)

    await waitFor(() => {
      expect(queryClient.getQueryState(matchesKey)?.isInvalidated).toBe(true)
    })
  })

  it('invalidates matches when a meta deck is updated', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const matchesKey = seedMatchesQuery(queryClient)
    vi.mocked(metaDecksApi.updateMetaDeck).mockResolvedValue({} as never)

    const { result } = renderHook(() => useUpdateMetaDeck(), { wrapper: wrapper(queryClient) })
    await result.current.mutateAsync({ deckId: 'md-1', payload: { name: 'New name' } as never })

    await waitFor(() => {
      expect(queryClient.getQueryState(matchesKey)?.isInvalidated).toBe(true)
    })
  })

  it('invalidates matches when a meta deck is archived', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const matchesKey = seedMatchesQuery(queryClient)
    vi.mocked(metaDecksApi.archiveMetaDeck).mockResolvedValue(undefined)

    const { result } = renderHook(() => useArchiveMetaDeck(), { wrapper: wrapper(queryClient) })
    await result.current.mutateAsync('md-1')

    await waitFor(() => {
      expect(queryClient.getQueryState(matchesKey)?.isInvalidated).toBe(true)
    })
  })
})
