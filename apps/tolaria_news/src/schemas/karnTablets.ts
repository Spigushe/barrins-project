import { z } from 'zod'

/**
 * Mirrors the Karn Tablets section of `apps/barrins_api`'s
 * `app/schemas/responses_tolaria_news.py` (ADR-13) — the `/metagame`,
 * `/archetypes`, `/trends` BFF routes. Kept in sync with that contract by
 * hand; the pages stay behind `VITE_FEATURE_KARN_TABLETS`.
 */

/** The two windowing modes the frontend can request (sent as `?window=`). */
export const windowModeSchema = z.enum(['rolling_30d', 'banlist_period'])
export type WindowMode = z.infer<typeof windowModeSchema>

/** Response-side `WindowOut.kind`: backend `TrendWindowMode` also carries
 *  `all_time`/`custom`, which the frontend never requests but may receive. */
export const windowKindSchema = z.enum([
  'rolling_30d',
  'banlist_period',
  'all_time',
  'custom',
])

export const windowSchema = z.object({
  kind: windowKindSchema,
  label: z.string(),
  date_from: z.iso.date(),
  date_to: z.iso.date(),
})
export type Window = z.infer<typeof windowSchema>

/** Backend `ArchetypeMomentum` — `deck_share` movement vs the previous run
 *  of the same window mode. The band that separates "stable" from
 *  "rising"/"falling" is a backend-owned domain rule; the frontend only
 *  renders the label it is handed. */
export const archetypeMomentumSchema = z.enum(['rising', 'falling', 'stable', 'new'])
export type ArchetypeMomentum = z.infer<typeof archetypeMomentumSchema>

/** A card name plus its resolved Scryfall id (`null` if unresolved) —
 *  enough for the card-image hover. Matches backend `CardRef`. */
export const cardRefSchema = z.object({
  name: z.string(),
  scryfall_id: z.string().nullable(),
})
export type CardRef = z.infer<typeof cardRefSchema>

export const archetypeSchema = z.object({
  id: z.string(),
  name: z.string(),
  //  1 for a solo commander, 2 for a partner pair, [] for no commander.
  commanders: z.array(cardRefSchema),
  deck_count: z.number(),
  deck_share: z.number(),
  //  `deck_share` (latest run) − `deck_share` (previous run) for this
  //  archetype; `null` when there is no previous run or `momentum === 'new'`.
  deck_share_delta: z.number().nullable(),
  momentum: archetypeMomentumSchema,
})
export type Archetype = z.infer<typeof archetypeSchema>

/** `previous_window` / `next_window` are the adjacent windows of the same
 *  kind (oldest→newest); `null` at either end. Navigate by re-requesting
 *  with `?at=<window.label>`. */
const windowNavFields = {
  window: windowSchema,
  previous_window: windowSchema.nullable(),
  next_window: windowSchema.nullable(),
}

export const metagameSnapshotSchema = z.object({
  format: z.string(),
  ...windowNavFields,
  archetypes: z.array(archetypeSchema),
})
export type MetagameSnapshot = z.infer<typeof metagameSnapshotSchema>

/** One row of a representative decklist (`/archetypes`). `is_land` is
 *  resolved server-side against `mj_cards`; the "signature cards" view
 *  lists the top non-land entries. */
export const representativeCardSchema = z.object({
  name: z.string(),
  qty: z.number(),
  scryfall_id: z.string().nullable(),
  is_land: z.boolean(),
  //  `false` only for a metagame-wide staple land (backend decides the
  //  field-prevalence threshold). The "signature cards" view shows only
  //  `is_signature` cards.
  is_signature: z.boolean(),
})
export type RepresentativeCard = z.infer<typeof representativeCardSchema>

/** `/archetypes` row — the `/metagame` archetype plus its aggregated
 *  representative mainboard. */
export const metagameArchetypeDetailSchema = archetypeSchema.extend({
  representative_mainboard: z.array(representativeCardSchema),
})
export type MetagameArchetypeDetail = z.infer<typeof metagameArchetypeDetailSchema>

/** `/archetypes` payload — same window framing as `MetagameSnapshot`
 *  (so the page carries the prev/next stepper) plus the detail rows;
 *  `archetypes` is a `?limit=&cursor=` slice, `Envelope.page` has the
 *  cursor. */
export const archetypeDetailPageSchema = z.object({
  format: z.string(),
  ...windowNavFields,
  archetypes: z.array(metagameArchetypeDetailSchema),
})
export type ArchetypeDetailPage = z.infer<typeof archetypeDetailPageSchema>

export const trendPointSchema = z.object({
  window: windowSchema,
  // `null` (not `0`) for a run in which this archetype had no cluster — the
  // frontend renders a gap. Matches backend `ArchetypeTrendPoint`.
  deck_share: z.number().nullable(),
})
export type TrendPoint = z.infer<typeof trendPointSchema>

export const trendSchema = z.object({
  archetype_id: z.string(),
  archetype_name: z.string(),
  commanders: z.array(cardRefSchema),
  points: z.array(trendPointSchema),
})
export type Trend = z.infer<typeof trendSchema>
