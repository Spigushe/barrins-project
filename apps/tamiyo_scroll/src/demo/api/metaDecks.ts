import type { MetaDeck, MetaDeckWrite } from '@/schemas/tamiyoScroll'
import { getStore, nextId, nowIso } from '../demoStore'

/** Mirrors `src/api/metaDecks.ts` — see `../api/types.ts` for the compile-time proof. */

/** Top8/presence in % — mirrors the backend's `@computed_field` exactly (0-100 scale,
 * never trusted from storage: recomputed on every read, same as the real response). */
function conversionOf(topEight: number, presence: number): number | null {
  return presence > 0 ? Math.round((topEight / presence) * 100 * 100) / 100 : null
}

export function listMetaDecks(
  options: { includeArchived?: boolean } = {},
): Promise<MetaDeck[]> {
  const store = getStore()
  const decks = options.includeArchived
    ? store.metaDecks
    : store.metaDecks.filter((deck) => deck.archived_at === null)
  return Promise.resolve(
    structuredClone(decks).map((deck) => ({
      ...deck,
      conversion: conversionOf(deck.top8, deck.presence),
    })),
  )
}

export function createMetaDeck(payload: MetaDeckWrite): Promise<MetaDeck> {
  const store = getStore()
  const deck: MetaDeck = {
    id: nextId(),
    name: payload.name,
    personal_deck_id: payload.personal_deck_id,
    tier: payload.tier,
    category: payload.category,
    decklist_notes: payload.decklist_notes ?? null,
    top8: payload.top8,
    presence: payload.presence,
    expected: payload.expected,
    tests_status: payload.tests_status ?? null,
    archived_at: null,
    conversion: conversionOf(payload.top8, payload.presence),
    is_readonly: false,
    shared_by: null,
    has_shared_data: false,
    is_multi_share: false,
  }
  store.metaDecks.push(deck)
  return Promise.resolve(structuredClone(deck))
}

export function updateMetaDeck(
  deckId: string,
  payload: MetaDeckWrite,
): Promise<MetaDeck> {
  const store = getStore()
  const deck = store.metaDecks.find((candidate) => candidate.id === deckId)
  if (!deck) throw new Error(`Demo meta deck not found: ${deckId}`)
  deck.name = payload.name
  deck.tier = payload.tier
  deck.category = payload.category
  deck.decklist_notes = payload.decklist_notes ?? null
  deck.top8 = payload.top8
  deck.presence = payload.presence
  deck.expected = payload.expected
  deck.tests_status = payload.tests_status ?? null
  deck.conversion = conversionOf(payload.top8, payload.presence)
  return Promise.resolve(structuredClone(deck))
}

export function archiveMetaDeck(deckId: string): Promise<void> {
  const store = getStore()
  const deck = store.metaDecks.find((candidate) => candidate.id === deckId)
  if (deck) deck.archived_at = nowIso()
  return Promise.resolve()
}
