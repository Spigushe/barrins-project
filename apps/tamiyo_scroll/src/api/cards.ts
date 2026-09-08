import { z } from 'zod'
import { apiRequest } from './client'

/** S17 item 2: partial-match card-name search for on-the-fly dropdowns.
 * Public endpoint (`/api/v1/cards/*`, not BFF-namespaced) — presentation
 * only, per the Added-Card dropdown's own design decision.
 *
 * `exclude_banned_in=duelcommander`: the card log is a Duel Commander
 * deck-tuning tool, so a card banned in the format is never a valid
 * swap-in — the backend drops those from the suggestions (cards it
 * doesn't track for the format are still returned; free-text entry is
 * unaffected). */
export function searchCardsByNamePrefix(query: string) {
  return apiRequest('/api/v1/cards/search-by-name-prefix', z.string().array(), {
    params: { q: query, exclude_banned_in: 'duelcommander' },
    requireAuth: false,
  })
}
