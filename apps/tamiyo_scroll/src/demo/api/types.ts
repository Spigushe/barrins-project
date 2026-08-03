import type * as cardTestsApi from '@/api/cardTests'
import type * as matchesApi from '@/api/matches'
import type * as metaDecksApi from '@/api/metaDecks'
import type * as personalDecksApi from '@/api/personalDecks'
import type * as sessionsApi from '@/api/sessions'
import type * as statsApi from '@/api/stats'
import type * as teamsApi from '@/api/teams'

/**
 * The real `src/api/*.ts` modules' shapes, derived with `typeof import(...)`.
 * Each `src/demo/api/*.ts` module is checked against the matching type here
 * (see `_typecheck.ts`) — if a demo function's signature drifts from its
 * real counterpart, `tsc -b` (`npm run build`) fails at that assignment.
 */
export type PersonalDecksApi = typeof personalDecksApi
export type MatchesApi = typeof matchesApi
export type MetaDecksApi = typeof metaDecksApi
export type CardTestsApi = typeof cardTestsApi
export type StatsApi = typeof statsApi
export type SessionsApi = typeof sessionsApi
export type TeamsApi = typeof teamsApi
