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

/** S15: structured content of one past version — only fetched once expanded,
 * and skipped entirely while the diff setting is on (the diff replaces this
 * view rather than sitting alongside it). */
export function useDecklistVersionView(
  deckId: string | null,
  versionId: string | null,
  enabled = true,
) {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['decklist-version-view', owner?.id ?? 'self', deckId, versionId],
    queryFn: () => personalDecksApi.getDecklistVersionView(deckId ?? '', versionId ?? ''),
    enabled: enabled && deckId !== null && versionId !== null,
  })
}

/** S15: only fetched once expanded AND the opt-in setting is enabled. */
export function useDecklistVersionDiff(
  deckId: string | null,
  versionId: string | null,
  enabled: boolean,
) {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['decklist-version-diff', owner?.id ?? 'self', deckId, versionId],
    queryFn: () => personalDecksApi.getDecklistVersionDiff(deckId ?? '', versionId ?? ''),
    enabled: enabled && deckId !== null && versionId !== null,
  })
}

function useInvalidateDecklist() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['decklist-versions'] })
    void queryClient.invalidateQueries({ queryKey: ['decklist-view'] })
    // S16: which card tests match a real decklist change depends on the
    // deck's whole version history, so it can shift when a version is
    // added or removed.
    void queryClient.invalidateQueries({ queryKey: ['card-tests-change-log'] })
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
      personalDecksApi.importMoxfield(deckId, moxfieldUrl),
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
