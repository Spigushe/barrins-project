import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as metaDecksApi from '@/api/metaDecks'
import type { MetaDeckWrite } from '@/schemas/tamiyoScroll'
import { useViewingOwner } from './useViewingOwner'

export function useMetaDecks() {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['meta-decks', owner?.id ?? 'self'],
    queryFn: () => metaDecksApi.listMetaDecks(),
  })
}

function useInvalidateMetaDecks() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['meta-decks'] })
    void queryClient.invalidateQueries({ queryKey: ['stats'] })
  }
}

export function useCreateMetaDeck() {
  const invalidate = useInvalidateMetaDecks()
  return useMutation({
    mutationFn: (payload: MetaDeckWrite) => metaDecksApi.createMetaDeck(payload),
    onSuccess: invalidate,
  })
}

export function useUpdateMetaDeck() {
  const invalidate = useInvalidateMetaDecks()
  return useMutation({
    mutationFn: ({ deckId, payload }: { deckId: string; payload: MetaDeckWrite }) =>
      metaDecksApi.updateMetaDeck(deckId, payload),
    onSuccess: invalidate,
  })
}

export function useArchiveMetaDeck() {
  const invalidate = useInvalidateMetaDecks()
  return useMutation({
    mutationFn: (deckId: string) => metaDecksApi.archiveMetaDeck(deckId),
    onSuccess: invalidate,
  })
}
