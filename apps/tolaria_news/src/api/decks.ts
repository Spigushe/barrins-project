import { deckDetailSchema } from '@/schemas/tolariaNews'
import { apiRequest } from './client'

export function getDeck(id: string) {
  return apiRequest(`/bff/tolaria-news/decks/${id}`, deckDetailSchema)
}
