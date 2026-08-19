import { statsSchema } from '@/schemas/tolariaNews'
import { apiRequest } from './client'

export function getStats() {
  return apiRequest('/bff/tolaria-news/stats', statsSchema)
}
