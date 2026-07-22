import { z } from 'zod'
import { matchSchema, type MatchWrite } from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function listMatches() {
  return apiRequest('/bff/tamiyo-scroll/matches', matchSchema.array(), {
    applyOwnerParam: true,
  })
}

export function createMatch(payload: MatchWrite) {
  return apiRequest('/bff/tamiyo-scroll/matches', matchSchema, {
    method: 'POST',
    body: payload,
  })
}

export function updateMatch(matchId: string, payload: MatchWrite) {
  return apiRequest(`/bff/tamiyo-scroll/matches/${matchId}`, matchSchema, {
    method: 'PUT',
    body: payload,
  })
}

export function deleteMatch(matchId: string) {
  return apiRequest(`/bff/tamiyo-scroll/matches/${matchId}`, z.void(), {
    method: 'DELETE',
  })
}
