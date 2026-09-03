import { useQuery } from '@tanstack/react-query'
import { searchCardsByNamePrefix } from '@/api/cards'

/** S17 item 2: the Added-Card dropdown's own minimum before it searches
 * — matches the doc'd "3 characters starts the search" behavior. */
export const CARD_NAME_SEARCH_MIN_LENGTH = 3

export function useCardNameSearch(query: string) {
  const trimmed = query.trim()
  return useQuery({
    queryKey: ['card-name-search', trimmed],
    queryFn: () => searchCardsByNamePrefix(trimmed),
    enabled: trimmed.length >= CARD_NAME_SEARCH_MIN_LENGTH,
    staleTime: 60_000,
  })
}
