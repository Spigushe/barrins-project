import { archetypeSummarySchema, matchupSummarySchema } from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function getArchetypeSummary() {
  return apiRequest(
    '/bff/tamiyo-scroll/archetype-summary',
    archetypeSummarySchema.array(),
    { applyOwnerParam: true },
  )
}

export function getMatchupSummary(options: { personalDeckId?: string } = {}) {
  return apiRequest('/bff/tamiyo-scroll/matchup-summary', matchupSummarySchema, {
    applyOwnerParam: true,
    params: { personal_deck_id: options.personalDeckId },
  })
}
