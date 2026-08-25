import { z } from 'zod'
import {
  cardTestEvaluationSchema,
  cardTestSchema,
  type CardTestEvaluationWrite,
  type CardTestWrite,
} from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function listCardTests(options: { personalDeckId?: string } = {}) {
  return apiRequest('/bff/tamiyo-scroll/card-tests', cardTestSchema.array(), {
    applyOwnerParam: true,
    params: { personal_deck_id: options.personalDeckId },
  })
}

/** S16: card tests that don't match any real decklist change anywhere in
 * the deck's version history — the complement to the matched-card-test
 * comments shown inline on a decklist version's diff. */
export function listCardTestChangeLog(personalDeckId: string) {
  return apiRequest('/bff/tamiyo-scroll/card-tests/change-log', cardTestSchema.array(), {
    applyOwnerParam: true,
    params: { personal_deck_id: personalDeckId },
  })
}

export function createCardTest(payload: CardTestWrite) {
  return apiRequest('/bff/tamiyo-scroll/card-tests', cardTestSchema, {
    method: 'POST',
    body: payload,
  })
}

export function updateCardTest(testId: string, payload: CardTestWrite) {
  return apiRequest(`/bff/tamiyo-scroll/card-tests/${testId}`, cardTestSchema, {
    method: 'PUT',
    body: payload,
  })
}

export function deleteCardTest(testId: string) {
  return apiRequest(`/bff/tamiyo-scroll/card-tests/${testId}`, z.void(), {
    method: 'DELETE',
  })
}

export function createCardTestEvaluation(
  testId: string,
  payload: CardTestEvaluationWrite,
) {
  return apiRequest(
    `/bff/tamiyo-scroll/card-tests/${testId}/evaluations`,
    cardTestEvaluationSchema,
    { method: 'POST', body: payload },
  )
}

export function updateCardTestEvaluation(
  testId: string,
  evaluationId: string,
  payload: CardTestEvaluationWrite,
) {
  return apiRequest(
    `/bff/tamiyo-scroll/card-tests/${testId}/evaluations/${evaluationId}`,
    cardTestEvaluationSchema,
    { method: 'PUT', body: payload },
  )
}

export function deleteCardTestEvaluation(testId: string, evaluationId: string) {
  return apiRequest(
    `/bff/tamiyo-scroll/card-tests/${testId}/evaluations/${evaluationId}`,
    z.void(),
    { method: 'DELETE' },
  )
}
