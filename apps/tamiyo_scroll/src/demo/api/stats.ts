import type { ArchetypeSummary, MatchupSummary } from '@/schemas/tamiyoScroll'
import { getStore } from '../demoStore'
import { computeArchetypeSummary, computeMatchupSummary } from './statsCore'

/**
 * Mirrors `src/api/stats.ts` — see `../api/types.ts` for the compile-time
 * proof. Unlike the other demo modules this one derives its numbers from the
 * current in-memory matches rather than replaying a fixed fixture, so
 * adding/editing a match in the demo visibly moves the metagame stats too.
 * The actual math lives in `statsCore.ts`, mirroring
 * `app/services/tamiyo_scroll/stats.py`'s pure functions exactly.
 */

function matchesFor(personalDeckId: string | undefined) {
  const store = getStore()
  return store.matches.filter(
    (match) => personalDeckId === undefined || match.personal_deck_id === personalDeckId,
  )
}

export function getArchetypeSummary(
  options: { personalDeckId?: string } = {},
): Promise<ArchetypeSummary[]> {
  const store = getStore()
  const matches = matchesFor(options.personalDeckId)
  // Only active decks group into the archetype breakdown — matches `stats.py`'s
  // `get_archetype_summary` route, which pre-filters archived decks itself.
  const activeDecks = store.metaDecks.filter((deck) => deck.archived_at === null)
  return Promise.resolve(computeArchetypeSummary(activeDecks, matches))
}

export function getMatchupSummary(
  options: { personalDeckId?: string } = {},
): Promise<MatchupSummary> {
  const store = getStore()
  const matches = matchesFor(options.personalDeckId)
  // Every deck (archived included) so an opponent name still resolves for a
  // historical matchup row — matches `get_matchup_summary`'s `meta_decks_by_id`.
  const metaDecksById = new Map(store.metaDecks.map((deck) => [deck.id, deck]))
  return Promise.resolve(computeMatchupSummary(matches, metaDecksById))
}
