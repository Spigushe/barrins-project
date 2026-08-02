import { z } from 'zod'
import type { ArchetypeCategory, CardGame } from '@/schemas/tamiyoScroll'
import {
  decklistLineSchema,
  decklistVersionSchema,
  personalDeckSchema,
} from '@/schemas/tamiyoScroll'
import { apiRequest, apiRequestBlob } from './client'

export function listPersonalDecks(options: { includeArchived?: boolean } = {}) {
  return apiRequest('/bff/tamiyo-scroll/personal-decks', personalDeckSchema.array(), {
    applyOwnerParam: true,
    params: { include_archived: options.includeArchived },
  })
}

export function createPersonalDeck(payload: {
  name: string
  game: CardGame
  category: ArchetypeCategory
}) {
  return apiRequest('/bff/tamiyo-scroll/personal-decks', personalDeckSchema, {
    method: 'POST',
    body: payload,
  })
}

export function archivePersonalDeck(deckId: string) {
  return apiRequest(`/bff/tamiyo-scroll/personal-decks/${deckId}`, z.void(), {
    method: 'DELETE',
  })
}

/** Partial update (S1 rename, S10/S11 game/category) — only provided fields change. */
export function updatePersonalDeck(
  deckId: string,
  payload: { name?: string; game?: CardGame; category?: ArchetypeCategory },
) {
  return apiRequest(`/bff/tamiyo-scroll/personal-decks/${deckId}`, personalDeckSchema, {
    method: 'PATCH',
    body: payload,
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

export function importMoxfield(deckId: string, moxfieldUrl: string) {
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

/** Server-rendered PDF report for this deck's last 30 days (S5), no session required. */
export function getDeckReportPdf(deckId: string) {
  return apiRequestBlob(`/bff/tamiyo-scroll/personal-decks/${deckId}/report.pdf`)
}
