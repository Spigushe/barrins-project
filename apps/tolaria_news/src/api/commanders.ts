import {
  commanderTrendsResponseSchema,
  type TrendWindowMode,
} from '@/schemas/tolariaNews'
import { apiRequest } from './client'

export function getTrendingCommanders(
  mode: TrendWindowMode,
  periodOffset?: number,
  dateFrom?: string,
  dateTo?: string,
) {
  return apiRequest(
    '/bff/tolaria-news/decks/commanders/trending',
    commanderTrendsResponseSchema,
    {
      params: {
        mode,
        period_offset: periodOffset,
        date_from: dateFrom,
        date_to: dateTo,
      },
    },
  )
}
