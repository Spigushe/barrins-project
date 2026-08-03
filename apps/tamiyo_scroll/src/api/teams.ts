import { z } from 'zod'
import {
  memberDeckSchema,
  teamDeckMessageSchema,
  teamDeckSchema,
  teamSchema,
  teamSummarySchema,
} from '@/schemas/tamiyoScroll'
import { apiRequest, apiRequestBlob } from './client'

export function listMyTeams() {
  return apiRequest('/bff/tamiyo-scroll/teams/mine', teamSummarySchema.array())
}

export function getTeam(teamId: string) {
  return apiRequest(`/bff/tamiyo-scroll/teams/${teamId}`, teamSchema)
}

export function createTeam(name: string) {
  return apiRequest('/bff/tamiyo-scroll/teams', teamSchema, {
    method: 'POST',
    body: { name },
  })
}

export function joinTeam(inviteCode: string) {
  return apiRequest('/bff/tamiyo-scroll/teams/join', teamSchema, {
    method: 'POST',
    body: { invite_code: inviteCode },
  })
}

export function updateTeamDescription(teamId: string, description: string | null) {
  return apiRequest(`/bff/tamiyo-scroll/teams/${teamId}`, teamSchema, {
    method: 'PATCH',
    body: { description },
  })
}

export function deleteTeam(teamId: string, inviteCode: string) {
  return apiRequest(`/bff/tamiyo-scroll/teams/${teamId}`, z.void(), {
    method: 'DELETE',
    body: { invite_code: inviteCode },
  })
}

export function leaveTeam(teamId: string) {
  return apiRequest(`/bff/tamiyo-scroll/teams/${teamId}/leave`, z.void(), {
    method: 'POST',
  })
}

export function removeTeamMember(teamId: string, userId: string) {
  return apiRequest(`/bff/tamiyo-scroll/teams/${teamId}/members/${userId}`, z.void(), {
    method: 'DELETE',
  })
}

/** "Team Decks" — name-deduplicated rows (S2, name-based sharing). */
export function listTeamDecks(teamId: string) {
  return apiRequest(`/bff/tamiyo-scroll/teams/${teamId}/decks`, teamDeckSchema.array())
}

/** Every current member's own decks — owner-only, the flagging picker's pool. */
export function listMemberDecks(teamId: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/teams/${teamId}/members/decks`,
    memberDeckSchema.array(),
  )
}

/** Owner-only: flags `deckId`'s *name* into the team's rotation. */
export function flagTeamDeck(teamId: string, deckId: string) {
  return apiRequest(`/bff/tamiyo-scroll/teams/${teamId}/decks/flags`, teamDeckSchema, {
    method: 'POST',
    body: { deck_id: deckId },
  })
}

/** Owner-only: removes a flagged name — every member's matching deck drops out at once. */
export function unflagTeamDeck(teamId: string, nameKey: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/teams/${teamId}/decks/flags/${encodeURIComponent(nameKey)}`,
    z.void(),
    { method: 'DELETE' },
  )
}

/** Cumulative PDF for a team-flagged deck name — one report per name, not per owner. */
export function getTeamDeckReportPdf(teamId: string, nameKey: string) {
  return apiRequestBlob(
    `/bff/tamiyo-scroll/teams/${teamId}/decks/${encodeURIComponent(nameKey)}/report.pdf`,
  )
}

export function enableTeamDeckThread(teamId: string, nameKey: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/teams/${teamId}/decks/${encodeURIComponent(nameKey)}/thread`,
    z.void(),
    { method: 'POST' },
  )
}

export function listTeamDeckThreadMessages(teamId: string, nameKey: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/teams/${teamId}/decks/${encodeURIComponent(nameKey)}/thread/messages`,
    teamDeckMessageSchema.array(),
  )
}

export function postTeamDeckThreadMessage(teamId: string, nameKey: string, body: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/teams/${teamId}/decks/${encodeURIComponent(nameKey)}/thread/messages`,
    teamDeckMessageSchema,
    { method: 'POST', body: { body } },
  )
}
