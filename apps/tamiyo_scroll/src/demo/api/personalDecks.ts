import type {
  ArchetypeCategory,
  CardGame,
  DecklistCard,
  DecklistCardCategory,
  DecklistLine,
  DecklistTypeGroup,
  DecklistVersion,
  DecklistView,
  PersonalDeck,
} from '@/schemas/tamiyoScroll'
import { getStore, nextId, nowIso } from '../demoStore'

/**
 * Mirrors `src/api/personalDecks.ts` function-for-function (see
 * `../api/types.ts` for the compile-time proof) — backed by the in-memory
 * demo store instead of `barrins_api`.
 */

// Mirrors `commander_section_indices`/`parse_card_line`
// (apps/barrins_api/app/services/tamiyo_scroll/decklist_coloring.py) so the
// demo view groups cards the same way the real backend does. No card
// resolution happens here though (no `mj_cards` in the browser) — pip/
// oracle-text/image fields are always null for demo decks.
const CARD_LINE_PATTERN = /(\d+)[xX]?\s+(.*)/

function parseCardLine(line: string): { qty: number; name: string } | null {
  const stripped = line.trim()
  if (!stripped) return null
  const match = CARD_LINE_PATTERN.exec(stripped)
  if (!match) return null
  return { qty: Number(match[1]), name: match[2].trim() }
}

function commanderSectionIndices(lines: string[]): Set<number> {
  const indices = new Set<number>()
  let inSection = false
  lines.forEach((raw, index) => {
    const stripped = raw.trim()
    if (stripped.toLowerCase() === 'commander') {
      inSection = true
      return
    }
    if (inSection) {
      if (!stripped) {
        inSection = false
        return
      }
      indices.add(index)
    }
  })
  return indices
}

// Mirrors `categorize`/`group_by_category`
// (apps/barrins_api/app/services/decklist_sort.py) so the demo view groups
// cards the same way the real backend does. No card resolution happens
// here (no `mj_cards` in the browser), so `type_line` is always null and
// every demo card categorizes as "other" -- kept general so this stays
// correct if demo decks ever get typed data.
const CATEGORY_ORDER: DecklistCardCategory[] = [
  'planeswalker',
  'battle',
  'creature',
  'instant',
  'sorcery',
  'artifact',
  'enchantment',
  'land',
]

function categorize(typeLine: string | null): DecklistCardCategory {
  if (typeLine !== null) {
    const lowered = typeLine.toLowerCase()
    const match = CATEGORY_ORDER.find((category) => lowered.includes(category))
    if (match) return match
  }
  return 'other'
}

function groupByCategory(cards: DecklistCard[]): DecklistTypeGroup[] {
  const buckets = new Map<DecklistCardCategory, DecklistCard[]>()
  for (const card of cards) {
    const category = categorize(card.type_line)
    const bucket = buckets.get(category)
    if (bucket) bucket.push(card)
    else buckets.set(category, [card])
  }
  const groups: DecklistTypeGroup[] = []
  for (const category of [...CATEGORY_ORDER, 'other' as const]) {
    const categoryCards = buckets.get(category)
    if (categoryCards)
      groups.push({ category, count: categoryCards.length, cards: categoryCards })
  }
  return groups
}

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

export function getDecklistView(deckId: string): Promise<DecklistView> {
  const store = getStore()
  const storedLines = store.decklistLines[deckId] ?? []
  const commanderIdx = commanderSectionIndices(storedLines.map((l) => l.line))

  const commanderCards: DecklistCard[] = []
  const libraryCards: DecklistCard[] = []
  const unparsedLines: DecklistLine[] = []

  storedLines.forEach((line, index) => {
    const stripped = line.line.trim()
    if (!stripped || stripped.toLowerCase() === 'commander') return
    const parsed = parseCardLine(line.line)
    if (!parsed) {
      unparsedLines.push({ line: line.line, status: line.status })
      return
    }
    const card: DecklistCard = {
      qty: parsed.qty,
      name: parsed.name,
      status: line.status,
      mana_cost: null,
      type_line: null,
      text: null,
      keywords: [],
      scryfall_id: null,
    }
    ;(commanderIdx.has(index) ? commanderCards : libraryCards).push(card)
  })

  return Promise.resolve(
    structuredClone({
      commander_cards: commanderCards,
      library_cards: groupByCategory(libraryCards),
      unparsed_lines: unparsedLines,
    }),
  )
}

/** Placeholder PDF blob — no WeasyPrint call, no network, just enough for the "Download report" button to work. */
export function getDeckReportPdf(_deckId: string): Promise<Blob> {
  return Promise.resolve(
    new Blob(['Demo mode — no real report is generated.'], { type: 'application/pdf' }),
  )
}
