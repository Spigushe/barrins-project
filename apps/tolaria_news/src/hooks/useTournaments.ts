import { useQuery } from '@tanstack/react-query'
import {
  listTournaments,
  getTournament,
  getTournamentDecks,
  getTournamentStandings,
  getTournamentBracket,
  type TournamentListFilters,
} from '@/api/tournaments'

export function useTournaments(filters: TournamentListFilters, cursor?: string) {
  return useQuery({
    queryKey: ['tournaments', filters, cursor],
    queryFn: () => listTournaments(filters, cursor),
  })
}

export function useTournament(id: string) {
  return useQuery({
    queryKey: ['tournament', id],
    queryFn: () => getTournament(id),
  })
}

export function useTournamentDecks(id: string, cursor?: string) {
  return useQuery({
    queryKey: ['tournament', id, 'decks', cursor],
    queryFn: () => getTournamentDecks(id, cursor),
  })
}

export function useTournamentStandings(id: string, cursor?: string) {
  return useQuery({
    queryKey: ['tournament', id, 'standings', cursor],
    queryFn: () => getTournamentStandings(id, cursor),
  })
}

export function useTournamentBracket(id: string) {
  return useQuery({
    queryKey: ['tournament', id, 'bracket'],
    queryFn: () => getTournamentBracket(id),
  })
}
