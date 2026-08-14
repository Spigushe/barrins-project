import { useQuery } from '@tanstack/react-query'
import { getDeck } from '@/api/decks'

export function useDeck(id: string) {
  return useQuery({
    queryKey: ['deck', id],
    queryFn: () => getDeck(id),
  })
}
