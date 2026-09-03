/** Base URL of the Barrin's Identity service Tamiyo Scroll authenticates against. */
export const IDENTITY_SERVICE_URL: string =
  (import.meta.env.VITE_IDENTITY_SERVICE_URL as string | undefined) ??
  'http://localhost:8001'

/**
 * Tamiyo Scroll runs Goblin Guide in cookie mode (ADR-18): it calls Barrin's
 * Identity directly and the refresh token lives in an `HttpOnly` cookie, never
 * in JS, so a reload / reopened tab stays logged in. The identity deployment
 * must set `REFRESH_COOKIE_ENABLED=true` and list this app's origin in
 * `ALLOWED_ORIGINS`.
 */
export const IDENTITY_COOKIE_MODE = true

/**
 * Origin of the standalone Goblin Guide app. The settings popup's "Manage my
 * account" button sends the user here (same tab) for identity-owned account
 * management — display name, email, password, account deletion — with a
 * `?return_to=…&return_label=…` so Goblin Guide can offer a link back.
 */
export const GOBLIN_GUIDE_URL: string =
  (import.meta.env.VITE_GOBLIN_GUIDE_URL as string | undefined) ?? 'http://localhost:5175'
