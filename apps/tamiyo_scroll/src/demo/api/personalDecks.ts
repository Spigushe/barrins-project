import type {
  ArchetypeCategory,
  CardGame,
  DecklistCard,
  DecklistCardCategory,
  DecklistCardDiff,
  DecklistCardDiffStatus,
  DecklistLine,
  DecklistLineDiff,
  DecklistLineStatus,
  DecklistTypeGroup,
  DecklistVersion,
  DecklistVersionDiff,
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

function viewFromLines(storedLines: DecklistLine[]): DecklistView {
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

  return {
    commander_cards: commanderCards,
    library_cards: groupByCategory(libraryCards),
    unparsed_lines: unparsedLines,
  }
}

export function getDecklistView(deckId: string): Promise<DecklistView> {
  const store = getStore()
  const storedLines = store.decklistLines[deckId] ?? []
  return Promise.resolve(structuredClone(viewFromLines(storedLines)))
}

/** S15: structured view of one specific past version's saved content.
 * Versions don't carry a per-line status in the demo store (only the
 * "current" editable decklist does, via `decklistLines`), so every line
 * gets the same neutral status here -- mirrors the real backend's
 * `color_decklist` default for a line no card test opines on. */
export function getDecklistVersionView(
  deckId: string,
  versionId: string,
): Promise<DecklistView> {
  const store = getStore()
  const version = store.decklistVersions.find(
    (candidate) => candidate.personal_deck_id === deckId && candidate.id === versionId,
  )
  if (!version) throw new Error(`Demo decklist version not found: ${versionId}`)
  const status: DecklistLineStatus = 'neutral'
  const lines: DecklistLine[] = version.content
    .split('\n')
    .map((line) => ({ line, status }))
  return Promise.resolve(structuredClone(viewFromLines(lines)))
}

function cardQuantities(content: string): {
  quantities: Map<string, number>
  commanderNames: Set<string>
} {
  const lines = content.split('\n')
  const commanderIdx = commanderSectionIndices(lines)
  const quantities = new Map<string, number>()
  const commanderNames = new Set<string>()
  lines.forEach((raw, index) => {
    const parsed = parseCardLine(raw)
    if (!parsed) return
    quantities.set(parsed.name, (quantities.get(parsed.name) ?? 0) + parsed.qty)
    if (commanderIdx.has(index)) commanderNames.add(parsed.name)
  })
  return { quantities, commanderNames }
}

function unparsedLinesOf(content: string): string[] {
  return content.split('\n').filter((raw) => {
    const stripped = raw.trim()
    if (!stripped || stripped.toLowerCase() === 'commander') return false
    return parseCardLine(raw) === null
  })
}

/** Mirrors `diff_decklist_cards`
 * (apps/barrins_api/app/services/tamiyo_scroll/decklist_diff.py) --
 * cards matched by name across the two contents rather than by line
 * position. `card_test_notes` is always empty here: matching a card
 * test to a diff line needs the same DB-backed name resolution as
 * `listCardTestChangeLog` skips for the same reason (see that
 * function's comment in ./cardTests.ts). */
function diffDecklistCards(oldContent: string, newContent: string): DecklistCardDiff[] {
  const old = cardQuantities(oldContent)
  const next = cardQuantities(newContent)
  const names = [...new Set([...old.quantities.keys(), ...next.quantities.keys()])].sort()

  const cards: DecklistCardDiff[] = names.map((name) => {
    const oldQty = old.quantities.get(name) ?? null
    const newQty = next.quantities.get(name) ?? null
    let status: DecklistCardDiffStatus
    if (oldQty === null) status = 'added'
    else if (newQty === null) status = 'removed'
    else if (oldQty !== newQty) status = 'quantity_changed'
    else status = 'unchanged'
    const isCommander =
      next.commanderNames.has(name) || (newQty === null && old.commanderNames.has(name))
    return {
      name,
      status,
      old_qty: oldQty,
      new_qty: newQty,
      is_commander: isCommander,
      card_test_notes: [],
    }
  })

  cards.sort((a, b) => {
    if (a.is_commander !== b.is_commander) return a.is_commander ? -1 : 1
    return a.name.localeCompare(b.name)
  })
  return cards
}

/** Minimal LCS-based line diff -- mirrors `difflib.SequenceMatcher`'s
 * equal/removed/added opcodes closely enough for the demo's unparsed
 * (non-card) lines, which are typically short (headers, free-text
 * notes). */
function diffLines(oldLines: string[], newLines: string[]): DecklistLineDiff[] {
  const m = oldLines.length
  const n = newLines.length
  const lcs: number[][] = Array.from({ length: m + 1 }, () =>
    new Array<number>(n + 1).fill(0),
  )
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      lcs[i][j] =
        oldLines[i] === newLines[j]
          ? lcs[i + 1][j + 1] + 1
          : Math.max(lcs[i + 1][j], lcs[i][j + 1])
    }
  }

  const result: DecklistLineDiff[] = []
  let i = 0
  let j = 0
  while (i < m && j < n) {
    if (oldLines[i] === newLines[j]) {
      result.push({ line: oldLines[i], status: 'unchanged' })
      i++
      j++
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      result.push({ line: oldLines[i], status: 'removed' })
      i++
    } else {
      result.push({ line: newLines[j], status: 'added' })
      j++
    }
  }
  while (i < m) {
    result.push({ line: oldLines[i], status: 'removed' })
    i++
  }
  while (j < n) {
    result.push({ line: newLines[j], status: 'added' })
    j++
  }
  return result
}

/** S15: card-aware diff of `versionId` against the immediately-prior
 * version (by `version` number), mirroring `get_decklist_version_diff`.
 * No prior version -> empty diff with `compared_to_version: null`. */
export function getDecklistVersionDiff(
  deckId: string,
  versionId: string,
): Promise<DecklistVersionDiff> {
  const store = getStore()
  const version = store.decklistVersions.find(
    (candidate) => candidate.personal_deck_id === deckId && candidate.id === versionId,
  )
  if (!version) throw new Error(`Demo decklist version not found: ${versionId}`)

  const prior = store.decklistVersions
    .filter(
      (candidate) =>
        candidate.personal_deck_id === deckId && candidate.version < version.version,
    )
    .sort((a, b) => b.version - a.version)[0]

  if (!prior) {
    return Promise.resolve({
      version_id: version.id,
      version: version.version,
      compared_to_version_id: null,
      compared_to_version: null,
      cards: [],
      unparsed_lines: [],
    })
  }

  return Promise.resolve(
    structuredClone({
      version_id: version.id,
      version: version.version,
      compared_to_version_id: prior.id,
      compared_to_version: prior.version,
      cards: diffDecklistCards(prior.content, version.content),
      unparsed_lines: diffLines(
        unparsedLinesOf(prior.content),
        unparsedLinesOf(version.content),
      ),
    }),
  )
}

/** Placeholder PDF blob — no WeasyPrint call, no network, just enough for the "Download report" button to work. */
export function getDeckReportPdf(_deckId: string): Promise<Blob> {
  return Promise.resolve(
    new Blob(['Demo mode — no real report is generated.'], { type: 'application/pdf' }),
  )
}
