import { useQuery } from '@tanstack/react-query'
import * as statsApi from '@/api/stats'
import { useViewingOwner } from './useViewingOwner'

export function useArchetypeSummary() {
  const owner = useViewingOwner()
  return useQuery({
    queryKey: ['stats', 'archetype-summary', owner?.id ?? 'self'],
    queryFn: statsApi.getArchetypeSummary,
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
