import {
  tournamentSummarySchema,
  tournamentDetailSchema,
  deckSummarySchema,
  standingRowSchema,
  roundOutSchema,
  type BSSource,
} from '@/schemas/tolariaNews'
import { apiRequest } from './client'

export interface TournamentListFilters {
  source?: BSSource
  format?: string
  dateFrom?: string
  dateTo?: string
}

export function listTournaments(
  filters: TournamentListFilters = {},
  cursor?: string,
  limit = 20,
) {
  return apiRequest('/bff/tolaria-news/tournaments', tournamentSummarySchema.array(), {
    params: {
      source: filters.source,
      format: filters.format,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      cursor,
      limit,
    },
  })
}

export function getTournament(id: string) {
  return apiRequest(`/bff/tolaria-news/tournaments/${id}`, tournamentDetailSchema)
}

export function getTournamentDecks(id: string, cursor?: string, limit = 20) {
  return apiRequest(
    `/bff/tolaria-news/tournaments/${id}/decks`,
    deckSummarySchema.array(),
    { params: { cursor, limit } },
  )
}

export function getTournamentStandings(id: string, cursor?: string, limit = 20) {
  return apiRequest(
    `/bff/tolaria-news/tournaments/${id}/standings`,
    standingRowSchema.array(),
    { params: { cursor, limit } },
  )
}

export function getTournamentBracket(id: string) {
  return apiRequest(`/bff/tolaria-news/tournaments/${id}/bracket`, roundOutSchema.array())
}
