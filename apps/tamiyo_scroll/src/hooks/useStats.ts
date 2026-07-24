import { useQuery } from '@tanstack/react-query'
import * as statsApi from '@/api/stats'
import { useViewingOwner } from './useViewingOwner'

export function useArchetypeSummary(personalDeckId: string | null) {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['stats', 'archetype-summary', owner?.id ?? 'self', personalDeckId],
    queryFn: () =>
      statsApi.getArchetypeSummary({ personalDeckId: personalDeckId ?? undefined }),
  })
}

export function useMatchupSummary(personalDeckId: string | null) {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['stats', 'matchup-summary', owner?.id ?? 'self', personalDeckId],
    queryFn: () =>
      statsApi.getMatchupSummary({ personalDeckId: personalDeckId ?? undefined }),
  })
}
