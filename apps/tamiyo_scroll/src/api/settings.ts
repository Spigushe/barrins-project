import { userSettingsSchema } from '@/schemas/tamiyoScroll'
import { apiRequest } from './client'

export function getMySettings() {
  return apiRequest('/bff/tamiyo-scroll/me/settings', userSettingsSchema)
}

export function updateMySettings(payload: {
  data_shared?: boolean
  receive_shared_data?: boolean
  active_personal_deck_id?: string | null
  metagame_roster_scope?: 'game' | 'personal_deck'
  auto_archive_stale_sessions?: boolean
  auto_archive_decklist_version_gap?: number
  show_decklist_version_diff?: boolean
  validate_removed_card_in_decklist?: boolean
  validate_added_card_exists?: boolean
  show_decklist_change_log?: boolean
}) {
  return apiRequest('/bff/tamiyo-scroll/me/settings', userSettingsSchema, {
    method: 'PATCH',
    body: payload,
  })
}
