import { useQuery } from '@tanstack/react-query'
import { getTrendingCommanders } from '@/api/commanders'
import type { TrendWindowMode } from '@/schemas/tolariaNews'

export function useTrendingCommanders(mode: TrendWindowMode, periodOffset?: number) {
  return useQuery({
    queryKey: ['commanders', 'trending', mode, periodOffset],
    queryFn: () => getTrendingCommanders(mode, periodOffset),
  })
}
