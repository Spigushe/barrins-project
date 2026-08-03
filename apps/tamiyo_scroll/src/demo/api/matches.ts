import type { Match, MatchWrite } from '@/schemas/tamiyoScroll'
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

export function createMatch(payload: MatchWrite): Promise<Match> {
  const store = getStore()
  const match: Match = {
    id: nextId(),
    date: today(),
    personal_deck_id: payload.personal_deck_id,
    opponent_deck_id: payload.opponent_deck_id,
    decklist_version_id: payload.decklist_version_id ?? null,
    session_id: payload.session_id ?? null,
    on_play: payload.on_play,
    game1: payload.game1 ?? null,
    game2: payload.game2 ?? null,
    game3: payload.game3 ?? null,
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
  match.on_play = payload.on_play
  match.game1 = payload.game1 ?? null
  match.game2 = payload.game2 ?? null
  match.game3 = payload.game3 ?? null
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
