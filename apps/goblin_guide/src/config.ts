/** Base URL of the Barrin's Identity service this shell talks to. */
export const IDENTITY_SERVICE_URL: string =
  (import.meta.env.VITE_IDENTITY_SERVICE_URL as string | undefined) ??
  'http://localhost:8001'

/**
 * Goblin Guide runs in cookie mode (ADR-18): it calls Barrin's Identity
 * directly and the refresh token lives in an `HttpOnly` cookie, never in JS.
 * The identity deployment must set `REFRESH_COOKIE_ENABLED=true` and list this
 * app's origin in `ALLOWED_ORIGINS`.
 */
export const IDENTITY_COOKIE_MODE = true
