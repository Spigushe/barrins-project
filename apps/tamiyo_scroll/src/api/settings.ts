import { z } from 'zod'
import { availableSharerSchema, sharedUserSchema, userSettingsSchema } from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function getMySettings() {
  return apiRequest('/bff/tamiyo-scroll/me/settings', userSettingsSchema)
}

export function updateMySettings(payload: {
  data_shared?: boolean
  active_personal_deck_id?: string | null
}) {
  return apiRequest('/bff/tamiyo-scroll/me/settings', userSettingsSchema, {
    method: 'PATCH',
    body: payload,
  })
}

export function listSharedUsers() {
  return apiRequest('/bff/tamiyo-scroll/shared-users', sharedUserSchema.array())
}

export function listAvailableSharers() {
  return apiRequest('/bff/tamiyo-scroll/available-sharers', availableSharerSchema.array())
}

export function createReceiveOptIn(sharerId: string) {
  return apiRequest('/bff/tamiyo-scroll/receive-opt-ins', availableSharerSchema, {
    method: 'POST',
    body: { sharer_id: sharerId },
  })
}

export function deleteReceiveOptIn(sharerId: string) {
  return apiRequest(`/bff/tamiyo-scroll/receive-opt-ins/${sharerId}`, z.void(), {
    method: 'DELETE',
  })
}
