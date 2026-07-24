import { z } from 'zod'
import { cardTestSchema, type CardTestWrite } from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function listCardTests(options: { personalDeckId?: string } = {}) {
  return apiRequest('/bff/tamiyo-scroll/card-tests', cardTestSchema.array(), {
    applyOwnerParam: true,
    params: { personal_deck_id: options.personalDeckId },
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
