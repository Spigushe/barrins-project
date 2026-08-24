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
  'pending',
])
export type DecklistLineStatus = z.infer<typeof decklistLineStatusSchema>

export const metagameRosterScopeSchema = z.enum(['game', 'personal_deck'])
export type MetagameRosterScope = z.infer<typeof metagameRosterScopeSchema>

export const userSettingsSchema = z.object({
  data_shared: z.boolean(),
  receive_shared_data: z.boolean(),
  active_personal_deck_id: z.uuid().nullable(),
  metagame_roster_scope: metagameRosterScopeSchema,
  // S14 item 9: auto-archiving of stale sessions, opted-in by default.
  auto_archive_stale_sessions: z.boolean(),
  auto_archive_decklist_version_gap: z.number().int(),
  // S15: defaults true — when on, expanding a version in
  // VersionHistorySection shows its diff against the prior version
  // instead of its full content.
  show_decklist_version_diff: z.boolean(),
  // S16: opt-in write-time validations for card tests, both default false.
  validate_removed_card_in_decklist: z.boolean(),
  validate_added_card_exists: z.boolean(),
  // S16: gates both the matched-card-test comments on decklist diffs and
  // the standalone unmatched-entries list on the current decklist.
  show_decklist_change_log: z.boolean(),
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
  // Null only for a foreign (is_readonly) row merged in from a sharer
  // (F10) — never the sharer's own personal_deck_id.
  personal_deck_id: z.uuid().nullable(),
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
  // Every underlying id this row represents (F10) — [id] normally, or
  // every id a game-scope collapse folded together. Resolve a match's
  // opponent_deck_id against this, not just `id`, or a match referencing
  // a merged-away duplicate won't be found.
  merged_ids: z.array(z.uuid()).default([]),
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

export const cardTestEvaluationSchema = z.object({
  id: z.uuid(),
  test_id: z.uuid(),
  opponent_deck_id: z.uuid(),
  rating: z.number().int(),
  notes: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
})
export type CardTestEvaluation = z.infer<typeof cardTestEvaluationSchema>

export const cardTestSchema = z.object({
  id: z.uuid(),
  personal_deck_id: z.uuid().nullable(),
  removed_card_name: z.string(),
  added_card_name: z.string(),
  notes: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  evaluations: z.array(cardTestEvaluationSchema),
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
  pending_added_card_name: z.string().nullable().optional(),
  pending_added_card_scryfall_id: z.string().nullable().optional(),
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

export const decklistCardDiffStatusSchema = z.enum([
  'added',
  'removed',
  'unchanged',
  'quantity_changed',
])
export type DecklistCardDiffStatus = z.infer<typeof decklistCardDiffStatusSchema>

export const decklistCardDiffSchema = z.object({
  name: z.string(),
  status: decklistCardDiffStatusSchema,
  old_qty: z.number().int().nullable(),
  new_qty: z.number().int().nullable(),
  is_commander: z.boolean(),
  // S16: notes from any card test whose removed/added card matches this
  // line — always present, rendering gated by `show_decklist_change_log`.
  card_test_notes: z.array(z.string()),
})
export type DecklistCardDiff = z.infer<typeof decklistCardDiffSchema>

export const decklistLineDiffSchema = z.object({
  line: z.string(),
  status: z.enum(['added', 'removed', 'unchanged']),
})
export type DecklistLineDiff = z.infer<typeof decklistLineDiffSchema>

// S15: card-aware diff of one decklist version against the immediately-prior
// one. `compared_to_version` is null for the deck's first version — no
// prior version exists to diff against.
export const decklistVersionDiffSchema = z.object({
  version_id: z.uuid(),
  version: z.number().int(),
  compared_to_version_id: z.uuid().nullable(),
  compared_to_version: z.number().int().nullable(),
  cards: z.array(decklistCardDiffSchema),
  unparsed_lines: z.array(decklistLineDiffSchema),
})
export type DecklistVersionDiff = z.infer<typeof decklistVersionDiffSchema>

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
  // Required (F10) — every roster entry is created for a specific deck.
  personal_deck_id: z.uuid(),
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
  removed_card_name: z.string().min(1).max(255),
  added_card_name: z.string().min(1).max(255),
  notes: z.string().nullable().optional(),
})
export type CardTestWrite = z.infer<typeof cardTestWriteSchema>

export const cardTestEvaluationWriteSchema = z.object({
  opponent_deck_id: z.uuid(),
  rating: z.number().int().min(1).max(5),
  notes: z.string().nullable().optional(),
})
export type CardTestEvaluationWrite = z.infer<typeof cardTestEvaluationWriteSchema>

export const sessionSchema = z.object({
  id: z.uuid(),
  owner_id: z.uuid(),
  personal_deck_id: z.uuid(),
  name: z.string(),
  type: sessionTypeSchema,
  notes: z.string().nullable(),
  location: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
  // S14: freely user-editable, no workflow meaning — see `closed_at`.
  started_at: z.iso.datetime({ offset: true }).nullable(),
  ended_at: z.iso.datetime({ offset: true }).nullable(),
  // Close/Reopen workflow state (the pre-S14 `ended_at`) — drives the
  // Status ("Ongoing"/"Closed") badge.
  closed_at: z.iso.datetime({ offset: true }).nullable(),
  archived_at: z.iso.datetime({ offset: true }).nullable(),
  hue: z.number().int().nullable(),
})
export type Session = z.infer<typeof sessionSchema>

export const sessionCreateSchema = z.object({
  name: z.string().min(1).max(255),
  type: sessionTypeSchema,
  personal_deck_id: z.uuid(),
  notes: z.string().nullable().optional(),
  location: z.string().nullable().optional(),
  started_at: z.iso.datetime({ offset: true }).nullable().optional(),
  ended_at: z.iso.datetime({ offset: true }).nullable().optional(),
  hue: z.number().int().min(0).max(359).nullable().optional(),
})
export type SessionCreate = z.infer<typeof sessionCreateSchema>

export const sessionPatchSchema = z.object({
  name: z.string().min(1).max(255).optional(),
  notes: z.string().nullable().optional(),
  location: z.string().nullable().optional(),
  started_at: z.iso.datetime({ offset: true }).nullable().optional(),
  ended_at: z.iso.datetime({ offset: true }).nullable().optional(),
  hue: z.number().int().min(0).max(359).nullable().optional(),
  close: z.boolean().optional(),
  reopen: z.boolean().optional(),
  restore: z.boolean().optional(),
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
  email: z.email(),
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

export const platformMetricsSchema = z.object({
  total_accounts: aggregateMetricSchema,
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

export const platformMetricsTimeseriesSchema = z.object({
  accounts: metricTimeseriesSchema,
  personal_decks: metricTimeseriesSchema,
  matches: metricTimeseriesSchema,
})
export type PlatformMetricsTimeseries = z.infer<typeof platformMetricsTimeseriesSchema>
