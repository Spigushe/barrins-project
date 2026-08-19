import { useQuery } from '@tanstack/react-query'
import {
  getDeck,
  getStaples,
  listCommanders,
  listDecks,
  type DeckListFilters,
} from '@/api/decks'

export function useDeck(id: string) {
  return useQuery({
    queryKey: ['deck', id],
    queryFn: () => getDeck(id),
  })
}

export function useDecks(filters: DeckListFilters, cursor?: string) {
  return useQuery({
    queryKey: ['decks', filters, cursor],
    queryFn: () => listDecks(filters, cursor),
  })
}

export function useCommanders() {
  return useQuery({
    queryKey: ['commanders'],
    queryFn: () => listCommanders(),
  })
}

export function useStaples(
  dateFrom: string | undefined,
  dateTo: string | undefined,
  commander: string | undefined,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ['decks', 'staples', dateFrom, dateTo, commander],
    queryFn: () => getStaples(dateFrom, dateTo, commander),
    enabled,
  })
}
