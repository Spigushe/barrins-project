import {
  metagameSnapshotSchema,
  archetypeSchema,
  trendSchema,
  type WindowMode,
} from '@/schemas/karnTablets'
import { apiRequest } from './client'

// PROVISIONAL — see src/schemas/karnTablets.ts. These routes don't exist in
// `barrins_api` yet (T4 iteration 2 / T6 not started); calls here 404 until
// that ships. Wired up ahead of time behind VITE_FEATURE_KARN_TABLETS.

export function getMetagame(windowMode: WindowMode) {
  return apiRequest('/bff/tolaria-news/metagame', metagameSnapshotSchema, {
    params: { window: windowMode },
  })
}

export function getArchetypes(windowMode: WindowMode) {
  return apiRequest('/bff/tolaria-news/archetypes', archetypeSchema.array(), {
    params: { window: windowMode },
  })
}

export function getTrends(windowMode: WindowMode) {
  return apiRequest('/bff/tolaria-news/trends', trendSchema.array(), {
    params: { window: windowMode },
  })
}
