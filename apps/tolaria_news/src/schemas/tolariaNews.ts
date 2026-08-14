import { z } from 'zod'

/**
 * Mirrors `apps/barrins_api/app/schemas/responses_tolaria_news.py` field for
 * field — that file is the source of truth for this shape, not this one.
 */

export const bsSourceSchema = z.enum(['mtgo', 'mtgtop8'])
export type BSSource = z.infer<typeof bsSourceSchema>

export const tournamentSummarySchema = z.object({
  id: z.uuid(),
  source: bsSourceSchema,
  date: z.iso.date(),
  name: z.string(),
  url: z.string(),
  format: z.string(),
  players: z.number(),
})
export type TournamentSummary = z.infer<typeof tournamentSummarySchema>

export const tournamentDetailSchema = tournamentSummarySchema.extend({
  deck_count: z.number(),
  standing_count: z.number(),
})
export type TournamentDetail = z.infer<typeof tournamentDetailSchema>

export const deckSummarySchema = z.object({
  id: z.uuid(),
  tournament_id: z.uuid(),
  date: z.iso.date(),
  player: z.string(),
  result: z.string().nullable(),
  anchor_uri: z.string(),
})
export type DeckSummary = z.infer<typeof deckSummarySchema>

export const commanderRefSchema = z.object({
  name: z.string(),
  scryfall_id: z.string().nullable(),
  color_identity: z.array(z.string()),
})
export type CommanderRef = z.infer<typeof commanderRefSchema>

export const deckCardOutSchema = z.object({
  name: z.string(),
  qty: z.number(),
  cmc: z.number().nullable(),
  type_line: z.string().nullable(),
  scryfall_id: z.string().nullable(),
})
export type DeckCardOut = z.infer<typeof deckCardOutSchema>

export const deckDetailSchema = deckSummarySchema.extend({
  notes: z.string().nullable(),
  commanders: z.array(commanderRefSchema),
  mainboard: z.array(deckCardOutSchema),
})
export type DeckDetail = z.infer<typeof deckDetailSchema>

export const standingRowSchema = z.object({
  rank: z.number(),
  player: z.string(),
  points: z.number(),
  wins: z.number(),
  losses: z.number(),
  draws: z.number(),
  omwp: z.number(),
  gwp: z.number(),
  ogwp: z.number(),
})
export type StandingRow = z.infer<typeof standingRowSchema>

export const roundMatchOutSchema = z.object({
  player_1: z.string(),
  player_2: z.string(),
  result: z.string(),
})
export type RoundMatchOut = z.infer<typeof roundMatchOutSchema>

export const roundOutSchema = z.object({
  round_name: z.string(),
  matches: z.array(roundMatchOutSchema),
})
export type RoundOut = z.infer<typeof roundOutSchema>
