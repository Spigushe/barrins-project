import type {
  ArchetypeCategory,
  CardGame,
  DecklistLine,
  DecklistVersion,
  PersonalDeck,
} from '@/schemas/tamiyoScroll'
import { getStore, nextId, nowIso } from '../demoStore'

/**
 * Mirrors `src/api/personalDecks.ts` function-for-function (see
 * `../api/types.ts` for the compile-time proof) — backed by the in-memory
 * demo store instead of `barrins_api`.
 */

export function listPersonalDecks(
  options: { includeArchived?: boolean } = {},
): Promise<PersonalDeck[]> {
  const store = getStore()
  const decks = options.includeArchived
    ? store.personalDecks
    : store.personalDecks.filter((deck) => deck.archived_at === null)
  return Promise.resolve(structuredClone(decks))
}

export function createPersonalDeck(payload: {
  name: string
  game: CardGame
  category: ArchetypeCategory
}): Promise<PersonalDeck> {
  const store = getStore()
  const deck: PersonalDeck = {
    id: nextId(),
    name: payload.name,
    game: payload.game,
    category: payload.category,
    archived_at: null,
    created_at: nowIso(),
  }
  store.personalDecks.push(deck)
  return Promise.resolve(structuredClone(deck))
}

export function archivePersonalDeck(deckId: string): Promise<void> {
  const store = getStore()
  const deck = store.personalDecks.find((candidate) => candidate.id === deckId)
  if (deck) deck.archived_at = nowIso()
  return Promise.resolve()
}

/** Partial update (S1 rename, S10/S11 game/category) — only provided fields change. */
export function updatePersonalDeck(
  deckId: string,
  payload: { name?: string; game?: CardGame; category?: ArchetypeCategory },
): Promise<PersonalDeck> {
  const store = getStore()
  const deck = store.personalDecks.find((candidate) => candidate.id === deckId)
  if (!deck) throw new Error(`Demo personal deck not found: ${deckId}`)
  if (payload.name !== undefined) deck.name = payload.name
  if (payload.game !== undefined) deck.game = payload.game
  if (payload.category !== undefined) deck.category = payload.category
  return Promise.resolve(structuredClone(deck))
}

export function listDecklistVersions(deckId: string): Promise<DecklistVersion[]> {
  const store = getStore()
  const versions = store.decklistVersions
    .filter((version) => version.personal_deck_id === deckId)
    .sort((a, b) => b.version - a.version)
  return Promise.resolve(structuredClone(versions))
}

export function createDecklistVersion(
  deckId: string,
  content: string,
): Promise<DecklistVersion> {
  const store = getStore()
  const currentMax = Math.max(
    0,
    ...store.decklistVersions
      .filter((version) => version.personal_deck_id === deckId)
      .map((version) => version.version),
  )
  const version: DecklistVersion = {
    id: nextId(),
    personal_deck_id: deckId,
    version: currentMax + 1,
    content,
    source: 'manual',
    created_at: nowIso(),
    moxfield_deck_changed_since_last_import: null,
  }
  store.decklistVersions.push(version)
  return Promise.resolve(structuredClone(version))
}

export function importMoxfield(
  deckId: string,
  moxfieldUrl: string,
): Promise<DecklistVersion> {
  const store = getStore()
  const currentMax = Math.max(
    0,
    ...store.decklistVersions
      .filter((version) => version.personal_deck_id === deckId)
      .map((version) => version.version),
  )
  const version: DecklistVersion = {
    id: nextId(),
    personal_deck_id: deckId,
    version: currentMax + 1,
    content: `// Demo import from ${moxfieldUrl}\n1 Aurelia, the Warleader\n1 Lightning Helix\n1 Sacred Foundry`,
    source: 'moxfield_import',
    created_at: nowIso(),
    moxfield_deck_changed_since_last_import: false,
  }
  store.decklistVersions.push(version)
  return Promise.resolve(structuredClone(version))
}

export function deleteDecklistVersion(deckId: string, versionId: string): Promise<void> {
  const store = getStore()
  store.decklistVersions = store.decklistVersions.filter(
    (version) => !(version.personal_deck_id === deckId && version.id === versionId),
  )
  return Promise.resolve()
}

export function getDecklistView(deckId: string): Promise<DecklistLine[]> {
  const store = getStore()
  return Promise.resolve(structuredClone(store.decklistLines[deckId] ?? []))
}

/** Placeholder PDF blob — no WeasyPrint call, no network, just enough for the "Download report" button to work. */
export function getDeckReportPdf(_deckId: string): Promise<Blob> {
  return Promise.resolve(
    new Blob(['Demo mode — no real report is generated.'], { type: 'application/pdf' }),
  )
}
