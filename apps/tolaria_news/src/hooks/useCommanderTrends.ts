import { useQuery } from '@tanstack/react-query'
import { getTrendingCommanders } from '@/api/commanders'
import type { TrendWindowMode } from '@/schemas/tolariaNews'

export function useTrendingCommanders(
  mode: TrendWindowMode,
  periodOffset?: number,
  dateFrom?: string,
  dateTo?: string,
) {
  return useQuery({
    queryKey: ['commanders', 'trending', mode, periodOffset, dateFrom, dateTo],
    queryFn: () => getTrendingCommanders(mode, periodOffset, dateFrom, dateTo),
  })
}
