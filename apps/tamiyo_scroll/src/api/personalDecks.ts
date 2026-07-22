import { z } from 'zod'
import {
  decklistLineSchema,
  decklistVersionSchema,
  personalDeckSchema,
} from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function listPersonalDecks(options: { includeArchived?: boolean } = {}) {
  return apiRequest('/bff/tamiyo-scroll/personal-decks', personalDeckSchema.array(), {
    applyOwnerParam: true,
    params: { include_archived: options.includeArchived },
  })
}

export function createPersonalDeck(name: string) {
  return apiRequest('/bff/tamiyo-scroll/personal-decks', personalDeckSchema, {
    method: 'POST',
    body: { name },
  })
}

export function archivePersonalDeck(deckId: string) {
  return apiRequest(`/bff/tamiyo-scroll/personal-decks/${deckId}`, z.void(), {
    method: 'DELETE',
  })
}

export function listDecklistVersions(deckId: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/personal-decks/${deckId}/versions`,
    decklistVersionSchema.array(),
    { applyOwnerParam: true },
  )
}

export function createDecklistVersion(deckId: string, content: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/personal-decks/${deckId}/versions`,
    decklistVersionSchema,
    { method: 'POST', body: { content } },
  )
}

export function importMoxfieldPlaceholder(deckId: string, moxfieldUrl: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/personal-decks/${deckId}/versions/import-moxfield`,
    decklistVersionSchema,
    { method: 'POST', body: { moxfield_url: moxfieldUrl } },
  )
}

export function deleteDecklistVersion(deckId: string, versionId: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/personal-decks/${deckId}/versions/${versionId}`,
    z.void(),
    { method: 'DELETE' },
  )
}

export function getDecklistView(deckId: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/personal-decks/${deckId}/decklist-view`,
    decklistLineSchema.array(),
    { applyOwnerParam: true },
  )
}
