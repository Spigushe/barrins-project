import { archetypeSummarySchema, matchupSummarySchema } from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function getArchetypeSummary(options: { personalDeckId?: string } = {}) {
  return apiRequest(
    '/bff/tamiyo-scroll/archetype-summary',
    archetypeSummarySchema.array(),
    {
      params: { personal_deck_id: options.personalDeckId },
    },
  )
}

export function getMatchupSummary(options: { personalDeckId?: string } = {}) {
  return apiRequest('/bff/tamiyo-scroll/matchup-summary', matchupSummarySchema, {
    params: { personal_deck_id: options.personalDeckId },
  })
}
