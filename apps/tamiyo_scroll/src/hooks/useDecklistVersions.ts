import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as personalDecksApi from '@/api/personalDecks'
import { useViewingOwner } from './useViewingOwner'

export function useDecklistVersions(deckId: string | null) {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['decklist-versions', owner?.id ?? 'self', deckId],
    queryFn: () => personalDecksApi.listDecklistVersions(deckId ?? ''),
    enabled: deckId !== null,
  })
}

export function useDecklistView(deckId: string | null) {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['decklist-view', owner?.id ?? 'self', deckId],
    queryFn: () => personalDecksApi.getDecklistView(deckId ?? ''),
    enabled: deckId !== null,
  })
}

function useInvalidateDecklist() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['decklist-versions'] })
    void queryClient.invalidateQueries({ queryKey: ['decklist-view'] })
  }
}

export function useCreateDecklistVersion() {
  const invalidate = useInvalidateDecklist()
  return useMutation({
    mutationFn: ({ deckId, content }: { deckId: string; content: string }) =>
      personalDecksApi.createDecklistVersion(deckId, content),
    onSuccess: invalidate,
  })
}

export function useImportMoxfield() {
  const invalidate = useInvalidateDecklist()
  return useMutation({
    mutationFn: ({ deckId, moxfieldUrl }: { deckId: string; moxfieldUrl: string }) =>
      personalDecksApi.importMoxfieldPlaceholder(deckId, moxfieldUrl),
    onSuccess: invalidate,
  })
}

export function useDeleteDecklistVersion() {
  const invalidate = useInvalidateDecklist()
  return useMutation({
    mutationFn: ({ deckId, versionId }: { deckId: string; versionId: string }) =>
      personalDecksApi.deleteDecklistVersion(deckId, versionId),
    onSuccess: invalidate,
  })
}
