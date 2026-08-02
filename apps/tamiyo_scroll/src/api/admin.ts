import {
  platformMetricsSchema,
  platformMetricsTimeseriesSchema,
} from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

/** Admin-only aggregate usage metrics (S6) — 403s for a non-admin caller. */
export function getPlatformMetrics() {
  return apiRequest('/bff/tamiyo-scroll/admin/metrics', platformMetricsSchema)
}

/** Admin-only day/week/month bucketed comparison of the same three metrics
 * above (added 2026-08-02) — 403s for a non-admin caller. */
export function getPlatformMetricsTimeseries() {
  return apiRequest(
    '/bff/tamiyo-scroll/admin/metrics/timeseries',
    platformMetricsTimeseriesSchema,
  )
}
