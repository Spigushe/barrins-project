import {
  metagameSnapshotSchema,
  archetypeDetailPageSchema,
  trendSchema,
  type WindowMode,
} from '@/schemas/karnTablets'
import { apiRequest } from './client'

// PROVISIONAL — see src/schemas/karnTablets.ts. Reachable only behind
// VITE_FEATURE_KARN_TABLETS.

export function getMetagame(windowMode: WindowMode, at?: string) {
  return apiRequest('/bff/tolaria-news/metagame', metagameSnapshotSchema, {
    params: { window: windowMode, at },
  })
}

export function getArchetypes(windowMode: WindowMode, at?: string, cursor?: string) {
  return apiRequest('/bff/tolaria-news/archetypes', archetypeDetailPageSchema, {
    params: { window: windowMode, at, cursor },
  })
}

export function getTrends(windowMode: WindowMode) {
  return apiRequest('/bff/tolaria-news/trends', trendSchema.array(), {
    params: { window: windowMode },
  })
}
