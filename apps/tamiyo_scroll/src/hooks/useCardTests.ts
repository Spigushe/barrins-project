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

function useInvalidateCardTests() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['card-tests'] })
    void queryClient.invalidateQueries({ queryKey: ['decklist-view'] })
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
