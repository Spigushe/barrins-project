import type {
  ArchetypeCategory,
  ArchetypeSummary,
  Match,
  MatchupRow,
  MatchupSummary,
} from '@/schemas/tamiyoScroll'
import { getStore } from '../demoStore'

/**
 * Mirrors `src/api/stats.ts` — see `../api/types.ts` for the compile-time
 * proof. Unlike the other demo modules this one derives its numbers from the
 * current in-memory matches rather than replaying a fixed fixture, so
 * adding/editing a match in the demo visibly moves the metagame stats too.
 */

type Outcome = 'win' | 'loss' | 'draw'

/** Same majority-of-three rule as `MatchJournalSection`'s display badge. */
function outcomeOf(match: Match): Outcome | null {
  const games = [match.game1, match.game2, match.game3].filter(
    (game): game is 'win' | 'loss' | 'draw' => game !== null,
  )
  const wins = games.filter((game) => game === 'win').length
  const losses = games.filter((game) => game === 'loss').length
  if (wins >= 2) return 'win'
  if (losses >= 2) return 'loss'
  if (games.length === 0) return null
  if (wins === 0 && losses >= 1) return 'loss'
  return 'draw'
}

function winrateOf(matches: Match[]): number | null {
  const decided = matches
    .map(outcomeOf)
    .filter((outcome): outcome is Outcome => outcome !== null)
  if (decided.length === 0) return null
  const score = decided.reduce(
    (sum, outcome) => sum + (outcome === 'win' ? 1 : outcome === 'draw' ? 0.5 : 0),
    0,
  )
  return score / decided.length
}

function ratioOf(matches: Match[]): string {
  const decided = matches
    .map(outcomeOf)
    .filter((outcome): outcome is Outcome => outcome !== null)
  const wins = decided.filter((outcome) => outcome === 'win').length
  const losses = decided.filter((outcome) => outcome === 'loss').length
  return `${String(wins)}-${String(losses)}`
}

function matchesFor(personalDeckId: string | undefined, opponentDeckId: string): Match[] {
  const store = getStore()
  return store.matches.filter(
    (match) =>
      match.opponent_deck_id === opponentDeckId &&
      (personalDeckId === undefined || match.personal_deck_id === personalDeckId),
  )
}

export function getArchetypeSummary(
  options: { personalDeckId?: string } = {},
): Promise<ArchetypeSummary[]> {
  const store = getStore()
  const active = store.metaDecks.filter((deck) => deck.archived_at === null)
  const categories = Array.from(new Set(active.map((deck) => deck.category)))

  const summaries: ArchetypeSummary[] = categories.map((category: ArchetypeCategory) => {
    const decksInCategory = active.filter((deck) => deck.category === category)
    const decks = decksInCategory.map((deck) => ({
      id: deck.id,
      name: deck.name,
      winrate: winrateOf(matchesFor(options.personalDeckId, deck.id)),
      is_readonly: false,
      has_shared_data: false,
    }))
    const known = decks
      .map((deck) => deck.winrate)
      .filter((rate): rate is number => rate !== null)
    const average_winrate =
      known.length > 0 ? known.reduce((a, b) => a + b, 0) / known.length : null
    return { category, average_winrate, decks }
  })

  return Promise.resolve(summaries)
}

export function getMatchupSummary(
  options: { personalDeckId?: string } = {},
): Promise<MatchupSummary> {
  const store = getStore()
  const active = store.metaDecks.filter((deck) => deck.archived_at === null)

  const rows: MatchupRow[] = active
    .map((deck): MatchupRow | null => {
      const matches = matchesFor(options.personalDeckId, deck.id)
      if (matches.length === 0) return null
      const otp = matches.filter((match) => match.on_play)
      const otd = matches.filter((match) => !match.on_play)
      return {
        opponent_deck_id: deck.id,
        opponent_deck_name: deck.name,
        winrate_global: winrateOf(matches),
        winrate_otp: winrateOf(otp),
        winrate_otd: winrateOf(otd),
        ratio_otp: ratioOf(otp),
        ratio_otd: ratioOf(otd),
        match_count: matches.length,
        is_readonly: false,
        has_shared_data: false,
      }
    })
    .filter((row): row is MatchupRow => row !== null)

  const known = rows
    .map((row) => row.winrate_global)
    .filter((rate): rate is number => rate !== null)
  const average_winrate =
    known.length > 0 ? known.reduce((a, b) => a + b, 0) / known.length : null

  return Promise.resolve({ rows, average_winrate })
}
