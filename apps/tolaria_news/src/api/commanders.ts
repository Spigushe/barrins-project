import {
  commanderTrendsResponseSchema,
  type TrendWindowMode,
} from '@/schemas/tolariaNews'
import { apiRequest } from './client'

export function getTrendingCommanders(mode: TrendWindowMode, periodOffset?: number) {
  return apiRequest(
    '/bff/tolaria-news/decks/commanders/trending',
    commanderTrendsResponseSchema,
    { params: { mode, period_offset: periodOffset } },
  )
}
