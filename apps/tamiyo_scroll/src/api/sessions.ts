import { z } from 'zod'
import {
  sessionComparisonSchema,
  sessionSchema,
  type SessionCreate,
  type SessionPatch,
} from '@/schemas/tamiyoScroll'
import { apiRequest, apiRequestBlob } from './client'

export function listSessions(personalDeckId: string, includeArchived = false) {
  return apiRequest('/bff/tamiyo-scroll/sessions', sessionSchema.array(), {
    params: {
      personal_deck_id: personalDeckId,
      include_archived: includeArchived,
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
