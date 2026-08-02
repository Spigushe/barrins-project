import { platformMetricsSchema } from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

/** Admin-only aggregate usage metrics (S6) — 403s for a non-admin caller. */
export function getPlatformMetrics() {
  return apiRequest('/bff/tamiyo-scroll/admin/metrics', platformMetricsSchema)
}
