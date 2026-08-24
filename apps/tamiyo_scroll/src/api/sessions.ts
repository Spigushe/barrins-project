import { z } from 'zod'
import {
  sessionComparisonSchema,
  sessionSchema,
  type SessionCreate,
  type SessionPatch,
} from '@/schemas/tamiyoScroll'
import { apiRequest, apiRequestBlob } from './client'

export interface ListSessionsOptions {
  limit?: number
  offset?: number
  sortBy?: 'name' | 'type' | 'started_at' | 'status'
  sortDir?: 'asc' | 'desc'
  search?: string
}

/** `options` are all optional and additive (S14) — omitting them returns
 * every matching session, unpaginated, exactly as before; the
 * match-logging session picker and the Match journal's session lookup
 * both rely on that default. */
export function listSessions(
  personalDeckId: string,
  includeArchived = false,
  options: ListSessionsOptions = {},
) {
  return apiRequest('/bff/tamiyo-scroll/sessions', sessionSchema.array(), {
    params: {
      personal_deck_id: personalDeckId,
      include_archived: includeArchived,
      limit: options.limit,
      offset: options.offset,
      sort_by: options.sortBy,
      sort_dir: options.sortDir,
      search: options.search,
    },
  })
}

export function createSession(payload: SessionCreate) {
  return apiRequest('/bff/tamiyo-scroll/sessions', sessionSchema, {
    method: 'POST',
    body: payload,
  })
}

export function updateSession(sessionId: string, payload: SessionPatch) {
  return apiRequest(`/bff/tamiyo-scroll/sessions/${sessionId}`, sessionSchema, {
    method: 'PATCH',
    body: payload,
  })
}

export function archiveSession(sessionId: string) {
  return apiRequest(`/bff/tamiyo-scroll/sessions/${sessionId}`, z.void(), {
    method: 'DELETE',
  })
}

export function getSessionComparison(sessionId: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/sessions/${sessionId}/comparison`,
    sessionComparisonSchema,
  )
}

/** Server-rendered PDF report for this session (S5) — WeasyPrint, backend-only. */
export function getSessionReportPdf(sessionId: string) {
  return apiRequestBlob(`/bff/tamiyo-scroll/sessions/${sessionId}/report.pdf`)
}
