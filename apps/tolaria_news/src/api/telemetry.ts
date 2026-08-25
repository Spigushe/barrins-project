import { telemetrySchema } from '@/schemas/tolariaNews'
import { apiRequest } from './client'

export function getTelemetry() {
  return apiRequest('/bff/tolaria-news/telemetry', telemetrySchema)
}
