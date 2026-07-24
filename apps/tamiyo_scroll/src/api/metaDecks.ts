import { z } from 'zod'
import { metaDeckSchema, type MetaDeckWrite } from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function listMetaDecks(options: { includeArchived?: boolean } = {}) {
  return apiRequest('/bff/tamiyo-scroll/meta-decks', metaDeckSchema.array(), {
    applyOwnerParam: true,
    params: { include_archived: options.includeArchived },
  })
}

export function createMetaDeck(payload: MetaDeckWrite) {
  return apiRequest('/bff/tamiyo-scroll/meta-decks', metaDeckSchema, {
    method: 'POST',
    body: payload,
  })
}

export function updateMetaDeck(deckId: string, payload: MetaDeckWrite) {
  return apiRequest(`/bff/tamiyo-scroll/meta-decks/${deckId}`, metaDeckSchema, {
    method: 'PUT',
    body: payload,
  })
}

export function archiveMetaDeck(deckId: string) {
  return apiRequest(`/bff/tamiyo-scroll/meta-decks/${deckId}`, z.void(), {
    method: 'DELETE',
  })
}
