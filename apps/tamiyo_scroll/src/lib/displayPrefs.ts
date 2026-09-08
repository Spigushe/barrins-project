/**
 * Client-side `localStorage` keys for Tamiyo Scroll's purely-visual
 * display preferences. Deliberately never synced to the backend
 * `UserSettings` model — see `s12-uiux-polish/index.md`'s "Design
 * decisions" for why (they're purely visual, adding them there would
 * mean a migration for something that never needs cross-account
 * visibility). Read via `useLocalStorageFlag`.
 *
 * The first four (S12) are toggled from `AccountSettingsDialog`'s
 * "Display" section; `DISPLAY_PREF_CURRENT_DECKLIST_COLLAPSED` (S19) is
 * toggled inline from the "Current decklist" section header instead.
 */
export const DISPLAY_PREF_MATCHUP_ROW_TINT = 'ts-matchup-row-tint-enabled'
export const DISPLAY_PREF_MATCHUP_RESULT_FORMAT_2W0L = 'ts-matchup-result-format-2w0l'
export const DISPLAY_PREF_ROSTER_ARCHETYPE_COLOR = 'ts-roster-archetype-color-enabled'
export const DISPLAY_PREF_ROSTER_TIER_COLOR = 'ts-roster-tier-color-enabled'

/** S19: fold state for the Decklist tab's "Current decklist" section.
 * `true` = collapsed (card tables hidden, header kept as the anchor). */
export const DISPLAY_PREF_CURRENT_DECKLIST_COLLAPSED = 'ts-current-decklist-collapsed'
