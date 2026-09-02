import { z } from 'zod'

export const archetypeCategorySchema = z.enum(['aggro', 'midrange', 'control', 'combo'])
export type ArchetypeCategory = z.infer<typeof archetypeCategorySchema>

export const cardGameSchema = z.enum([
  'magic',
  'yu_gi_oh',
  'pokemon',
  'flesh_and_blood',
  'one_piece',
  'lorcana',
  'star_wars_unlimited',
  'digimon',
  'cardfight_vanguard',
  'riftbound',
  'other',
])
export type CardGame = z.infer<typeof cardGameSchema>

export const expectedLevelSchema = z.enum([
  'as_expected',
  'more_expected',
  'less_expected',
])
export type ExpectedLevel = z.infer<typeof expectedLevelSchema>

export const gameResultSchema = z.enum(['win', 'loss', 'draw'])
export type GameResult = z.infer<typeof gameResultSchema>

export const decklistVersionSourceSchema = z.enum(['manual', 'moxfield_import'])
export type DecklistVersionSource = z.infer<typeof decklistVersionSourceSchema>

export const decklistLineStatusSchema = z.enum([
  'validated',
  'rejected',
  'in_test',
  'neutral',
])
export type DecklistLineStatus = z.infer<typeof decklistLineStatusSchema>

export const userSettingsSchema = z.object({
  data_shared: z.boolean(),
  receive_shared_data: z.boolean(),
  active_personal_deck_id: z.uuid().nullable(),
})
export type UserSettings = z.infer<typeof userSettingsSchema>

export const personalDeckSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  // Nullable (S10/S11) — NULL on a historical deck until PATCHed; gates
  // logging a match (backend 422) until set.
  game: cardGameSchema.nullable(),
  category: archetypeCategorySchema.nullable(),
  archived_at: z.iso.datetime({ offset: true }).nullable(),
  created_at: z.iso.datetime({ offset: true }),
})
export type PersonalDeck = z.infer<typeof personalDeckSchema>

export const decklistVersionSchema = z.object({
  id: z.uuid(),
  personal_deck_id: z.uuid(),
  version: z.number().int(),
  content: z.string(),
  source: decklistVersionSourceSchema,
  created_at: z.iso.datetime({ offset: true }),
  // Only set on the import-moxfield response itself (S3's opportunistic
  // staleness check) — null on every other decklist-version response.
  moxfield_deck_changed_since_last_import: z.boolean().nullable().default(null),
})
export type DecklistVersion = z.infer<typeof decklistVersionSchema>

export const metaDeckSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  tier: z.number(),
  category: archetypeCategorySchema,
  decklist_notes: z.string().nullable(),
  top8: z.number().int(),
  presence: z.number().int(),
  expected: expectedLevelSchema,
  tests_status: z.string().nullable(),
  archived_at: z.iso.datetime({ offset: true }).nullable(),
  conversion: z.number().nullable(),
  is_readonly: z.boolean(),
  shared_by: z.string().nullable().optional(),
  has_shared_data: z.boolean(),
  is_multi_share: z.boolean(),
})
export type MetaDeck = z.infer<typeof metaDeckSchema>

export const sessionTypeSchema = z.enum(['tournament', 'training'])
export type SessionType = z.infer<typeof sessionTypeSchema>

export const matchSchema = z.object({
  id: z.uuid(),
  date: z.iso.date(),
  personal_deck_id: z.uuid(),
  opponent_deck_id: z.uuid(),
  decklist_version_id: z.uuid().nullable(),
  session_id: z.uuid().nullable(),
  on_play: z.boolean(),
  game1: gameResultSchema.nullable(),
  game2: gameResultSchema.nullable(),
  game3: gameResultSchema.nullable(),
  opening_hand: z.string().nullable(),
  turning_point: z.string().nullable(),
  final_turn: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  is_readonly: z.boolean(),
  shared_by: z.string().nullable().optional(),
})
export type Match = z.infer<typeof matchSchema>

export const cardTestSchema = z.object({
  id: z.uuid(),
  personal_deck_id: z.uuid().nullable(),
  tester: z.string(),
  card_name: z.string(),
  opponent_deck_id: z.uuid().nullable(),
  rating: z.number().int(),
  notes: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
})
export type CardTest = z.infer<typeof cardTestSchema>

export const decklistLineSchema = z.object({
  line: z.string(),
  status: decklistLineStatusSchema,
})
export type DecklistLine = z.infer<typeof decklistLineSchema>

export const decklistCardSchema = z.object({
  qty: z.number().int(),
  name: z.string(),
  status: decklistLineStatusSchema,
  mana_cost: z.string().nullable(),
  type_line: z.string().nullable(),
  text: z.string().nullable(),
  keywords: z.array(z.string()),
  scryfall_id: z.string().nullable(),
})
export type DecklistCard = z.infer<typeof decklistCardSchema>

export const decklistCardCategorySchema = z.enum([
  'planeswalker',
  'battle',
  'creature',
  'instant',
  'sorcery',
  'artifact',
  'enchantment',
  'land',
  'other',
])
export type DecklistCardCategory = z.infer<typeof decklistCardCategorySchema>

export const decklistTypeGroupSchema = z.object({
  category: decklistCardCategorySchema,
  count: z.number().int(),
  cards: z.array(decklistCardSchema),
})
export type DecklistTypeGroup = z.infer<typeof decklistTypeGroupSchema>

export const decklistViewSchema = z.object({
  commander_cards: z.array(decklistCardSchema),
  library_cards: z.array(decklistTypeGroupSchema),
  unparsed_lines: z.array(decklistLineSchema),
})
export type DecklistView = z.infer<typeof decklistViewSchema>

export const deckWinrateSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  winrate: z.number().nullable(),
  is_readonly: z.boolean(),
  has_shared_data: z.boolean(),
})
export type DeckWinrate = z.infer<typeof deckWinrateSchema>

export const archetypeSummarySchema = z.object({
  category: archetypeCategorySchema,
  average_winrate: z.number().nullable(),
  decks: z.array(deckWinrateSchema),
})
export type ArchetypeSummary = z.infer<typeof archetypeSummarySchema>

export const matchupRowSchema = z.object({
  opponent_deck_id: z.uuid(),
  opponent_deck_name: z.string(),
  winrate_global: z.number().nullable(),
  winrate_otp: z.number().nullable(),
  winrate_otd: z.number().nullable(),
  ratio_otp: z.string(),
  ratio_otd: z.string(),
  match_count: z.number().int(),
  is_readonly: z.boolean(),
  has_shared_data: z.boolean(),
})
export type MatchupRow = z.infer<typeof matchupRowSchema>

export const matchupSummarySchema = z.object({
  rows: z.array(matchupRowSchema),
  average_winrate: z.number().nullable(),
})
export type MatchupSummary = z.infer<typeof matchupSummarySchema>

// ---------------------------------------------------------------------------
// Write payloads — mirror of the Pydantic request schemas (MetaDeckWrite,
// MatchWrite, CardTestWrite). Validated client-side before sending; the
// backend remains the source of truth and fully revalidates.
// ---------------------------------------------------------------------------

export const metaDeckWriteSchema = z.object({
  name: z.string().min(1).max(255),
  tier: z.number().min(0).max(3).multipleOf(0.5),
  category: archetypeCategorySchema,
  decklist_notes: z.string().nullable().optional(),
  top8: z.number().int().min(0),
  presence: z.number().int().min(0),
  expected: expectedLevelSchema,
  tests_status: z.string().nullable().optional(),
})
export type MetaDeckWrite = z.infer<typeof metaDeckWriteSchema>

export const matchWriteSchema = z.object({
  personal_deck_id: z.uuid(),
  opponent_deck_id: z.uuid(),
  decklist_version_id: z.uuid().nullable().optional(),
  session_id: z.uuid().nullable().optional(),
  on_play: z.boolean(),
  game1: gameResultSchema.nullable().optional(),
  game2: gameResultSchema.nullable().optional(),
  game3: gameResultSchema.nullable().optional(),
  opening_hand: z.string().nullable().optional(),
  turning_point: z.string().nullable().optional(),
  final_turn: z.string().nullable().optional(),
})
export type MatchWrite = z.infer<typeof matchWriteSchema>

export const cardTestWriteSchema = z.object({
  personal_deck_id: z.uuid(),
  tester: z.string().min(1).max(120),
  card_name: z.string().min(1).max(255),
  opponent_deck_id: z.uuid().nullable().optional(),
  rating: z.number().int().min(1).max(5),
  notes: z.string().nullable().optional(),
})
export type CardTestWrite = z.infer<typeof cardTestWriteSchema>

export const sessionSchema = z.object({
  id: z.uuid(),
  owner_id: z.uuid(),
  personal_deck_id: z.uuid(),
  name: z.string(),
  type: sessionTypeSchema,
  notes: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  ended_at: z.iso.datetime({ offset: true }).nullable(),
  archived_at: z.iso.datetime({ offset: true }).nullable(),
})
export type Session = z.infer<typeof sessionSchema>

export const sessionCreateSchema = z.object({
  name: z.string().min(1).max(255),
  type: sessionTypeSchema,
  personal_deck_id: z.uuid(),
  notes: z.string().nullable().optional(),
})
export type SessionCreate = z.infer<typeof sessionCreateSchema>

export const sessionPatchSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  notes: z.string().nullable().optional(),
  close: z.boolean().optional(),
  reopen: z.boolean().optional(),
})
export type SessionPatch = z.infer<typeof sessionPatchSchema>

export const sessionComparisonSchema = z.object({
  session: sessionSchema,
  session_match_count: z.number().int(),
  baseline_match_count: z.number().int(),
  session_wins: z.number().int(),
  session_losses: z.number().int(),
  baseline_wins: z.number().int(),
  baseline_losses: z.number().int(),
  session_archetype_summary: z.array(archetypeSummarySchema),
  baseline_archetype_summary: z.array(archetypeSummarySchema),
  session_matchup_summary: matchupSummarySchema,
  baseline_matchup_summary: matchupSummarySchema,
})
export type SessionComparison = z.infer<typeof sessionComparisonSchema>

export const teamSummarySchema = z.object({
  id: z.uuid(),
  name: z.string(),
  is_owner: z.boolean(),
})
export type TeamSummary = z.infer<typeof teamSummarySchema>

export const teamMemberSchema = z.object({
  user_id: z.uuid(),
  // Since the identity cutover (ADR-20) the roster carries the identity
  // handle + display name only — never the email. `null` when the identity
  // account is inactive / removed.
  username: z.string().nullable(),
  display_name: z.string().nullable(),
  is_owner: z.boolean(),
  joined_at: z.iso.datetime({ offset: true }),
  activity_count: z.number().int(),
})
export type TeamMember = z.infer<typeof teamMemberSchema>

export const teamSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  description: z.string().nullable(),
  invite_code: z.string(),
  owner_id: z.uuid(),
  created_at: z.iso.datetime({ offset: true }),
  members: z.array(teamMemberSchema),
})
export type Team = z.infer<typeof teamSchema>

export const teamDeckOwnerSchema = z.object({
  deck_id: z.uuid(),
  display: z.string(),
})
export type TeamDeckOwner = z.infer<typeof teamDeckOwnerSchema>

export const teamDeckSchema = z.object({
  name_key: z.string(),
  deck_name: z.string(),
  owners: z.array(teamDeckOwnerSchema),
  has_thread: z.boolean(),
})
export type TeamDeck = z.infer<typeof teamDeckSchema>

export const memberDeckSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  owner_id: z.uuid(),
  owner_display: z.string(),
  is_flagged: z.boolean(),
})
export type MemberDeck = z.infer<typeof memberDeckSchema>

export const teamDeckMessageSchema = z.object({
  id: z.uuid(),
  thread_id: z.uuid(),
  author_id: z.uuid(),
  author_display: z.string(),
  body: z.string(),
  created_at: z.iso.datetime({ offset: true }),
})
export type TeamDeckMessage = z.infer<typeof teamDeckMessageSchema>

// ---------------------------------------------------------------------------
// Admin usage/metrics dashboard (S6) — v2.0.0 ships exactly these three
// aggregate counts, nothing more (deeper metrics are explicitly deferred).
// ---------------------------------------------------------------------------

// v2.0.0 only ever populates "tamiyo_scroll" — see
// app/services/metrics/aggregates.py's `MetricSource` for why the tag
// exists at all (a v3.0.0 externalization seam, not overengineering).
export const metricSourceSchema = z.enum(['tamiyo_scroll'])
export type MetricSource = z.infer<typeof metricSourceSchema>

export const aggregateMetricSchema = z.object({
  value: z.number().int(),
  source: metricSourceSchema,
})
export type AggregateMetric = z.infer<typeof aggregateMetricSchema>

// `total_accounts` was dropped in the identity cutover (ADR-20) — `barrins_api`
// no longer owns a `users` table to count. Restore later via a
// `barrins_identity` admin count endpoint.
export const platformMetricsSchema = z.object({
  total_personal_decks: aggregateMetricSchema,
  total_matches: aggregateMetricSchema,
})
export type PlatformMetrics = z.infer<typeof platformMetricsSchema>

// Time-bucketed comparison (added 2026-08-02) — same three counts above,
// broken down per period instead of collapsed to one all-time total.
export const metricTimeseriesPointSchema = z.object({
  period_start: z.iso.datetime({ offset: true }),
  count: z.number().int(),
})
export type MetricTimeseriesPoint = z.infer<typeof metricTimeseriesPointSchema>

export const metricTimeseriesSchema = z.object({
  daily: z.array(metricTimeseriesPointSchema),
  weekly: z.array(metricTimeseriesPointSchema),
  monthly: z.array(metricTimeseriesPointSchema),
})
export type MetricTimeseries = z.infer<typeof metricTimeseriesSchema>

// `accounts` dropped alongside `total_accounts` (ADR-20).
export const platformMetricsTimeseriesSchema = z.object({
  personal_decks: metricTimeseriesSchema,
  matches: metricTimeseriesSchema,
})
export type PlatformMetricsTimeseries = z.infer<typeof platformMetricsTimeseriesSchema>
