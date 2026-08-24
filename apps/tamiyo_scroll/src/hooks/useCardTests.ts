import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as cardTestsApi from '@/api/cardTests'
import type { CardTestWrite } from '@/schemas/tamiyoScroll'
import { useViewingOwner } from './useViewingOwner'

export function useCardTests(personalDeckId: string | null) {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['card-tests', owner?.id ?? 'self', personalDeckId],
    queryFn: () =>
      cardTestsApi.listCardTests({ personalDeckId: personalDeckId ?? undefined }),
    enabled: personalDeckId !== null,
  })
}

/** S16: card tests for `personalDeckId` that don't match any real decklist
 * change anywhere in the deck's version history — used by the standalone
 * change-log list on the current decklist, only fetched when that display
 * is enabled. */
export function useCardTestChangeLog(personalDeckId: string | null, enabled: boolean) {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['card-tests-change-log', owner?.id ?? 'self', personalDeckId],
    queryFn: () => cardTestsApi.listCardTestChangeLog(personalDeckId ?? ''),
    enabled: enabled && personalDeckId !== null,
  })
}

function useInvalidateCardTests() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['card-tests'] })
    void queryClient.invalidateQueries({ queryKey: ['card-tests-change-log'] })
    void queryClient.invalidateQueries({ queryKey: ['decklist-view'] })
    // S16: a card test's match against a decklist diff can change without
    // the diff's own content changing (e.g. adding a new card test).
    void queryClient.invalidateQueries({ queryKey: ['decklist-version-diff'] })
  }
}

export function useCreateCardTest() {
  const invalidate = useInvalidateCardTests()
  return useMutation({
    mutationFn: (payload: CardTestWrite) => cardTestsApi.createCardTest(payload),
    onSuccess: invalidate,
  })
}

export function useUpdateCardTest() {
  const invalidate = useInvalidateCardTests()
  return useMutation({
    mutationFn: ({ testId, payload }: { testId: string; payload: CardTestWrite }) =>
      cardTestsApi.updateCardTest(testId, payload),
    onSuccess: invalidate,
  })
}

export function useDeleteCardTest() {
  const invalidate = useInvalidateCardTests()
  return useMutation({
    mutationFn: (testId: string) => cardTestsApi.deleteCardTest(testId),
    onSuccess: invalidate,
  })
}
