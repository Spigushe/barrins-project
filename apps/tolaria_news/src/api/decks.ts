import { z } from 'zod'
import {
  deckDetailSchema,
  deckListItemSchema,
  staplesResponseSchema,
  type BSSource,
} from '@/schemas/tolariaNews'
import { apiRequest } from './client'

export interface DeckListFilters {
  player?: string
  source?: BSSource
  commander?: string
  colors?: string[]
  sizes?: string[]
  dateFrom?: string
  dateTo?: string
}

export function listDecks(filters: DeckListFilters = {}, cursor?: string, limit = 20) {
  return apiRequest('/bff/tolaria-news/decks', deckListItemSchema.array(), {
    params: {
      player: filters.player,
      source: filters.source,
      commander: filters.commander,
      colors: filters.colors,
      sizes: filters.sizes,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      cursor,
      limit,
    },
  })
}

export function listCommanders() {
  return apiRequest('/bff/tolaria-news/decks/commanders', z.string().array())
}

export function getDeck(id: string) {
  return apiRequest(`/bff/tolaria-news/decks/${id}`, deckDetailSchema)
}

export function getStaples(dateFrom: string, dateTo: string) {
  return apiRequest('/bff/tolaria-news/decks/staples', staplesResponseSchema, {
    params: { date_from: dateFrom, date_to: dateTo },
  })
}
