import type {
  Match,
  MatchGame,
  MatchGameEvent,
  MatchGameEventWrite,
  MatchGameWrite,
  MatchWrite,
} from '@/schemas/tamiyoScroll'
import { getStore, nextId, nowIso } from '../demoStore'

/** Mirrors `src/api/matches.ts` — see `../api/types.ts` for the compile-time proof. */

export function listMatches(personalDeckId: string): Promise<Match[]> {
  const store = getStore()
  const matches = store.matches.filter(
    (match) => match.personal_deck_id === personalDeckId,
  )
  return Promise.resolve(structuredClone(matches))
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

/** D2's second amendment: every write event gets a fresh id — the demo
 * store doesn't attempt the real backend's "match an edited event to its
 * existing row by array position" in-place update (Consequences), it just
 * treats every save as a full replace, same as every other field here. An
 * omitted list is stored as `[]` ("tracked, zero events"), not `null` — the
 * demo doesn't simulate the NULL-vs-zero role-based distinction the real
 * backend makes for a sub-`moderator` caller. */
function eventsFromWrite(events: MatchGameEventWrite[] | undefined): MatchGameEvent[] {
  return (events ?? []).map((event) => ({
    id: nextId(),
    comment: event.comment ?? null,
  }))
}

/** #123/#124: mirrors `_apply_payload`'s nested `games[]` handling — every
 * entry the caller sent is stored as-is. */
function gamesFromWrite(games: MatchGameWrite[]): MatchGame[] {
  return games.map((game) => ({
    game_number: game.game_number,
    on_play: game.on_play,
    result: game.result ?? null,
    player_mulligans: eventsFromWrite(game.player_mulligans),
    opponent_mulligans: eventsFromWrite(game.opponent_mulligans),
    player_misplays: eventsFromWrite(game.player_misplays),
    opponent_misplays: eventsFromWrite(game.opponent_misplays),
  }))
}

export function createMatch(payload: MatchWrite): Promise<Match> {
  const store = getStore()
  const match: Match = {
    id: nextId(),
    date: today(),
    personal_deck_id: payload.personal_deck_id,
    opponent_deck_id: payload.opponent_deck_id,
    decklist_version_id: payload.decklist_version_id ?? null,
    session_id: payload.session_id ?? null,
    games: gamesFromWrite(payload.games),
    opening_hand: payload.opening_hand ?? null,
    turning_point: payload.turning_point ?? null,
    final_turn: payload.final_turn ?? null,
    created_at: nowIso(),
    is_readonly: false,
    shared_by: null,
  }
  store.matches.push(match)
  return Promise.resolve(structuredClone(match))
}

export function updateMatch(matchId: string, payload: MatchWrite): Promise<Match> {
  const store = getStore()
  const match = store.matches.find((candidate) => candidate.id === matchId)
  if (!match) throw new Error(`Demo match not found: ${matchId}`)
  match.personal_deck_id = payload.personal_deck_id
  match.opponent_deck_id = payload.opponent_deck_id
  match.decklist_version_id = payload.decklist_version_id ?? null
  match.session_id = payload.session_id ?? null
  match.games = gamesFromWrite(payload.games)
  match.opening_hand = payload.opening_hand ?? null
  match.turning_point = payload.turning_point ?? null
  match.final_turn = payload.final_turn ?? null
  return Promise.resolve(structuredClone(match))
}

export function deleteMatch(matchId: string): Promise<void> {
  const store = getStore()
  store.matches = store.matches.filter((match) => match.id !== matchId)
  return Promise.resolve()
}
