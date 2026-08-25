import { z } from 'zod'
import { apiRequest } from './client'

/** S17 item 2: partial-match card-name search for on-the-fly dropdowns.
 * Public endpoint (`/api/v1/cards/*`, not BFF-namespaced) — presentation
 * only, per the Added-Card dropdown's own design decision. */
export function searchCardsByNamePrefix(query: string) {
  return apiRequest('/api/v1/cards/search-by-name-prefix', z.string().array(), {
    params: { q: query },
    requireAuth: false,
  })
}
