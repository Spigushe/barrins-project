import type {
  ArchetypeCategory,
  ArchetypeSummary,
  Match,
  MatchupRow,
  MatchupSummary,
} from '@/schemas/tamiyoScroll'

/**
 * Mirrors `app/services/tamiyo_scroll/stats.py` exactly — game-level tally
 * (wins/losses counted per game in `match.games`, draws excluded from the
 * decisive denominator), percentages on a 0-100 scale. Split out from
 * `stats.ts` so `sessions.ts`'s comparison endpoint can reuse the same pure
 * functions on a session/baseline-scoped match list instead of the whole
 * store (Constitution §4.2 — no parallel calculation path).
 *
 * #123/#124 moved `on_play` from the match to each game (`ts_match_games`,
 * D1's "Full" normalization) — `onPlay` below now filters per game, not per
 * match, so "winrate on the play" correctly reflects who was on the play in
 * that specific game rather than the match's first game only.
 */

interface MetaDeckLike {
  id: string
  name: string
  category: ArchetypeCategory
  archived_at: string | null
}

export function tallyGames(
  matches: Match[],
  onPlay?: boolean,
): { wins: number; losses: number; draws: number } {
  let wins = 0
  let losses = 0
  let draws = 0
  for (const match of matches) {
    for (const game of match.games) {
      if (onPlay !== undefined && game.on_play !== onPlay) continue
      if (game.result === 'win') wins += 1
      else if (game.result === 'loss') losses += 1
      else if (game.result === 'draw') draws += 1
    }
  }
  return { wins, losses, draws }
}

/** #123/#124 D4/D5/D6: derived period metrics — London mulligan hand size
 * (`7 − mulligans`) and average misplays, both computed over the player's
 * own side only, across every game with that gated event list recorded (a
 * game where it's still `null` — never entered, or entered by a
 * sub-`moderator` who can't set it — is excluded from the average rather
 * than treated as 0). The real backend reads its own maintained integer
 * cache here rather than counting event rows on every request (D2's second
 * amendment); the demo has no such cache, so it derives the same number
 * from the event list's length — an explicitly sanctioned fallback for
 * anything not sourced directly from the real comparison endpoint. */
export function computeAvgHandSizeAndMisplays(matches: Match[]): {
  avg_hand_size: number | null
  avg_misplays: number | null
} {
  const mulligans: number[] = []
  const misplays: number[] = []
  for (const match of matches) {
    for (const game of match.games) {
      if (game.player_mulligans !== null) mulligans.push(game.player_mulligans.length)
      if (game.player_misplays !== null) misplays.push(game.player_misplays.length)
    }
  }
  const average = (values: number[]): number | null =>
    values.length === 0 ? null : values.reduce((a, b) => a + b, 0) / values.length

  const avgMulligans = average(mulligans)
  return {
    avg_hand_size: avgMulligans === null ? null : 7 - avgMulligans,
    avg_misplays: average(misplays),
  }
}

/** Winrate in % (draws excluded); null if no decisive game — matches `_winrate`. */
export function winrateOf(wins: number, losses: number): number | null {
  const decisive = wins + losses
  if (decisive === 0) return null
  return Math.round((wins / decisive) * 100 * 100) / 100
}

function ratioOf(wins: number, losses: number): string {
  return `${String(wins)}-${String(losses)}`
}

function matchesByOpponent(matches: Match[]): Map<string, Match[]> {
  const map = new Map<string, Match[]>()
  for (const match of matches) {
    const list = map.get(match.opponent_deck_id) ?? []
    list.push(match)
    map.set(match.opponent_deck_id, list)
  }
  return map
}

/** Mirrors `compute_archetype_summary` — average per archetype + each deck's own winrate. */
export function computeArchetypeSummary(
  metaDecks: MetaDeckLike[],
  matches: Match[],
): ArchetypeSummary[] {
  const active = metaDecks.filter((deck) => deck.archived_at === null)
  const byOpponent = matchesByOpponent(matches)
  const categories = Array.from(new Set(active.map((deck) => deck.category)))

  return categories.map((category) => {
    const decksInCategory = active.filter((deck) => deck.category === category)
    const decks = decksInCategory
      .map((deck) => {
        const { wins, losses } = tallyGames(byOpponent.get(deck.id) ?? [])
        return {
          id: deck.id,
          name: deck.name,
          winrate: winrateOf(wins, losses),
          is_readonly: false,
          has_shared_data: false,
        }
      })
      .sort((a, b) => a.name.localeCompare(b.name))

    const known = decks
      .map((deck) => deck.winrate)
      .filter((rate): rate is number => rate !== null)
    const average_winrate =
      known.length > 0
        ? Math.round((known.reduce((a, b) => a + b, 0) / known.length) * 100) / 100
        : null

    return { category, average_winrate, decks }
  })
}

/** Mirrors `compute_matchup_summary` — one row per opponent faced + an overall average
 * computed across all games (not an average of the per-row averages). */
export function computeMatchupSummary(
  matches: Match[],
  metaDecksById: Map<string, MetaDeckLike>,
): MatchupSummary {
  const byOpponent = matchesByOpponent(matches)

  const rows: MatchupRow[] = Array.from(byOpponent.entries())
    .map(([opponentId, opponentMatches]): MatchupRow => {
      const { wins, losses } = tallyGames(opponentMatches)
      const otp = tallyGames(opponentMatches, true)
      const otd = tallyGames(opponentMatches, false)
      const deck = metaDecksById.get(opponentId)
      return {
        opponent_deck_id: opponentId,
        opponent_deck_name: deck?.name ?? '?',
        winrate_global: winrateOf(wins, losses),
        winrate_otp: winrateOf(otp.wins, otp.losses),
        winrate_otd: winrateOf(otd.wins, otd.losses),
        ratio_otp: ratioOf(otp.wins, otp.losses),
        ratio_otd: ratioOf(otd.wins, otd.losses),
        match_count: opponentMatches.length,
        is_readonly: false,
        has_shared_data: false,
      }
    })
    .sort((a, b) => a.opponent_deck_name.localeCompare(b.opponent_deck_name))

  const total = tallyGames(matches)
  const average_winrate = winrateOf(total.wins, total.losses)

  return { rows, average_winrate }
}
