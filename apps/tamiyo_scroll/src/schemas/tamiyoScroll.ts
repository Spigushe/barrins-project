import { z } from 'zod'

export const archetypeCategorySchema = z.enum(['aggro', 'midrange', 'control', 'combo'])
export type ArchetypeCategory = z.infer<typeof archetypeCategorySchema>

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
  active_personal_deck_id: z.uuid().nullable(),
})
export type UserSettings = z.infer<typeof userSettingsSchema>

export const sharedUserSchema = z.object({
  id: z.uuid(),
  display_name: z.string().nullable(),
  email: z.email(),
})
export type SharedUser = z.infer<typeof sharedUserSchema>

export const personalDeckSchema = z.object({
  id: z.uuid(),
  name: z.string(),
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
})
export type MetaDeck = z.infer<typeof metaDeckSchema>

export const matchSchema = z.object({
  id: z.uuid(),
  date: z.iso.date(),
  personal_deck_id: z.uuid(),
  opponent_deck_id: z.uuid(),
  on_play: z.boolean(),
  game1: gameResultSchema.nullable(),
  game2: gameResultSchema.nullable(),
  game3: gameResultSchema.nullable(),
  opening_hand: z.string().nullable(),
  turning_point: z.string().nullable(),
  final_turn: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
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

export const deckWinrateSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  winrate: z.number().nullable(),
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
})
export type MatchupRow = z.infer<typeof matchupRowSchema>

export const matchupSummarySchema = z.object({
  rows: z.array(matchupRowSchema),
  average_winrate: z.number().nullable(),
})
export type MatchupSummary = z.infer<typeof matchupSummarySchema>

// ---------------------------------------------------------------------------
// Payloads d'écriture — miroir des schémas de requête Pydantic (MetaDeckWrite,
// MatchWrite, CardTestWrite). Validés côté client avant envoi ; le backend
// reste la source de vérité et revalide intégralement.
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
