import * as demoCardTestsApi from './cardTests'
import * as demoMatchesApi from './matches'
import * as demoMetaDecksApi from './metaDecks'
import * as demoPersonalDecksApi from './personalDecks'
import * as demoStatsApi from './stats'
import type {
  CardTestsApi,
  MatchesApi,
  MetaDecksApi,
  PersonalDecksApi,
  StatsApi,
} from './types'

/**
 * Not imported or executed anywhere — this file exists purely so `tsc -b`
 * (`npm run build`) fails loudly the moment a demo module's exported
 * function signatures stop matching the real `src/api/*.ts` module they
 * mirror. See `types.ts` for how each interface is derived.
 */
export const personalDecksTypeCheck: PersonalDecksApi = demoPersonalDecksApi
export const matchesTypeCheck: MatchesApi = demoMatchesApi
export const metaDecksTypeCheck: MetaDecksApi = demoMetaDecksApi
export const cardTestsTypeCheck: CardTestsApi = demoCardTestsApi
export const statsTypeCheck: StatsApi = demoStatsApi
