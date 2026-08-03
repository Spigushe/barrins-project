/**
 * `localStorage` keys for S12's four opt-in/opt-out display preferences.
 * Deliberately client-side only, never synced to the backend
 * `UserSettings` model — see `s12-uiux-polish/index.md`'s "Design
 * decisions" for why (they're purely visual, adding them there would
 * mean a migration for something that never needs cross-account
 * visibility). Toggled from `AccountSettingsDialog`'s "Display" section,
 * read via `useLocalStorageFlag`.
 */
export const DISPLAY_PREF_MATCHUP_ROW_TINT = 'ts-matchup-row-tint-enabled'
export const DISPLAY_PREF_MATCHUP_RESULT_FORMAT_2W0L = 'ts-matchup-result-format-2w0l'
export const DISPLAY_PREF_ROSTER_ARCHETYPE_COLOR = 'ts-roster-archetype-color-enabled'
export const DISPLAY_PREF_ROSTER_TIER_COLOR = 'ts-roster-tier-color-enabled'
