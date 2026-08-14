import { z } from 'zod'

/**
 * PROVISIONAL. T6 ("Karn Tablets") is "Not started" and no
 * `/metagame`/`/archetypes`/`/trends` route exists in `apps/barrins_api`
 * today (T4 iteration 2, see ADR-13 in
 * docs/content/ops/architecture/decisions.md). These schemas are a
 * best-effort placeholder built from ADR-13's decided shape — push-based,
 * Duel-Commander-only input (no `format` param), two selectable windowing
 * modes (rolling 30-day vs. banlist-period) — not a confirmed API contract.
 * Reconcile against the real `responses_tolaria_news.py` additions once T4
 * iteration 2 actually ships.
 */

export const windowModeSchema = z.enum(['rolling_30d', 'banlist_period'])
export type WindowMode = z.infer<typeof windowModeSchema>

export const windowSchema = z.object({
  mode: windowModeSchema,
  label: z.string(),
  start: z.iso.date(),
  end: z.iso.date(),
})
export type Window = z.infer<typeof windowSchema>

export const archetypeSchema = z.object({
  id: z.string(),
  name: z.string(),
  deck_count: z.number(),
  deck_share: z.number(),
})
export type Archetype = z.infer<typeof archetypeSchema>

export const metagameSnapshotSchema = z.object({
  window: windowSchema,
  archetypes: z.array(archetypeSchema),
})
export type MetagameSnapshot = z.infer<typeof metagameSnapshotSchema>

export const trendPointSchema = z.object({
  window: windowSchema,
  deck_share: z.number(),
})
export type TrendPoint = z.infer<typeof trendPointSchema>

export const trendSchema = z.object({
  archetype_id: z.string(),
  archetype_name: z.string(),
  points: z.array(trendPointSchema),
})
export type Trend = z.infer<typeof trendSchema>
