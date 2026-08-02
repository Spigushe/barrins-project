import type {
  CardTest,
  DecklistLine,
  DecklistVersion,
  Match,
  MetaDeck,
  PersonalDeck,
  Session,
} from '@/schemas/tamiyoScroll'
import fixturesJson from './fixtures.json'

/**
 * In-memory demo dataset (S7). Seeded once from `fixtures.json` and mutated
 * in place by the demo API modules — never written back to disk, never sent
 * over the network. A full page reload re-evaluates this module from
 * scratch, which is what actually makes "nothing persists" true; `reset()`
 * additionally lets `DemoModeProvider` force a clean slate on mount, in case
 * a visitor reaches `/demo` more than once without a full reload in between.
 */
interface Fixtures {
  personalDecks: PersonalDeck[]
  metaDecks: MetaDeck[]
  matches: Match[]
  cardTests: CardTest[]
  decklistVersions: DecklistVersion[]
  decklistLines: Record<string, DecklistLine[]>
  sessions: Session[]
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function freshFixtures(): Fixtures {
  return clone(fixturesJson as unknown as Fixtures)
}

class DemoStore {
  personalDecks: PersonalDeck[]
  metaDecks: MetaDeck[]
  matches: Match[]
  cardTests: CardTest[]
  decklistVersions: DecklistVersion[]
  decklistLines: Record<string, DecklistLine[]>
  sessions: Session[]

  constructor() {
    const data = freshFixtures()
    this.personalDecks = data.personalDecks
    this.metaDecks = data.metaDecks
    this.matches = data.matches
    this.cardTests = data.cardTests
    this.decklistVersions = data.decklistVersions
    this.decklistLines = data.decklistLines
    this.sessions = data.sessions
  }
}

let store = new DemoStore()

/** The active in-memory dataset. Never persisted. */
export function getStore(): DemoStore {
  return store
}

/** Discards all in-session edits and reseeds from `fixtures.json`. */
export function resetDemoStore(): void {
  store = new DemoStore()
}

export function nextId(): string {
  return crypto.randomUUID()
}

export function nowIso(): string {
  return new Date().toISOString()
}
