import type {
  CardTest,
  DecklistLine,
  DecklistVersion,
  Match,
  MetaDeck,
  PersonalDeck,
  Session,
  TeamDeckMessage,
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

/** A demo team's member's own personal deck — the "flag a deck" picker's pool. */
export interface DemoMemberDeck {
  id: string
  name: string
  owner_id: string
  owner_display: string
}

export interface DemoTeamMember {
  user_id: string
  email: string
  display_name: string | null
  is_owner: boolean
  joined_at: string
  activity_count: number
}

/** Internal team shape — richer than the wire `Team`/`TeamSummary` schemas
 * (adds the member-deck pool + per-name-key flags/threads the real backend
 * derives from separate tables). `demo/api/teams.ts` projects this down to
 * the wire shapes on every read, same spirit as `metaDecks.ts`'s `conversion`. */
export interface DemoTeam {
  id: string
  name: string
  description: string | null
  invite_code: string
  owner_id: string
  created_at: string
  members: DemoTeamMember[]
  memberDecks: DemoMemberDeck[]
  /** Lowercased/trimmed deck names currently flagged into the team's rotation. */
  flaggedNameKeys: string[]
  /** Keyed by the same name key; presence of a key (even with an empty array)
   * means the discussion thread has been enabled for that name. */
  threads: Record<string, TeamDeckMessage[]>
}

interface Fixtures {
  personalDecks: PersonalDeck[]
  metaDecks: MetaDeck[]
  matches: Match[]
  cardTests: CardTest[]
  decklistVersions: DecklistVersion[]
  decklistLines: Record<string, DecklistLine[]>
  sessions: Session[]
  currentUser: { id: string; email: string; display_name: string | null }
  teams: DemoTeam[]
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
  teams: DemoTeam[]

  constructor() {
    const data = freshFixtures()
    this.personalDecks = data.personalDecks
    this.metaDecks = data.metaDecks
    this.matches = data.matches
    this.cardTests = data.cardTests
    this.decklistVersions = data.decklistVersions
    this.decklistLines = data.decklistLines
    this.sessions = data.sessions
    this.teams = data.teams
  }
}

let store = new DemoStore()

/** The one fixed "you" identity for the demo session — teams/ownership
 * checks use this instead of the real (token-gated) `useCurrentUser`, so
 * the demo never needs to fake an access token. See `DemoTeamsSection`. */
export const DEMO_CURRENT_USER_ID: string = fixturesJson.currentUser.id

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
