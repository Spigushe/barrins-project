import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as matchesApi from '@/api/matches'
import type { MatchWrite } from '@/schemas/tamiyoScroll'
import { useViewingOwner } from './useViewingOwner'

export function useMatches() {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['matches', owner?.id ?? 'self'],
    queryFn: matchesApi.listMatches,
  })
}

function useInvalidateMatches() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['matches'] })
    void queryClient.invalidateQueries({ queryKey: ['stats'] })
  }
}

export function useCreateMatch() {
  const invalidate = useInvalidateMatches()
  return useMutation({
    mutationFn: (payload: MatchWrite) => matchesApi.createMatch(payload),
    onSuccess: invalidate,
  })
}

export function useUpdateMatch() {
  const invalidate = useInvalidateMatches()
  return useMutation({
    mutationFn: ({ matchId, payload }: { matchId: string; payload: MatchWrite }) =>
      matchesApi.updateMatch(matchId, payload),
    onSuccess: invalidate,
  })
}

export function useDeleteMatch() {
  const invalidate = useInvalidateMatches()
  return useMutation({
    mutationFn: (matchId: string) => matchesApi.deleteMatch(matchId),
    onSuccess: invalidate,
  })
}
