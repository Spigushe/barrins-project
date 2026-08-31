import { z } from 'zod'

/**
 * Wire shapes for the Barrin's Identity endpoints Goblin Guide consumes.
 * Login slice — see `docs/content/back/barrins_identity/integration.md` §4.1;
 * signup + email verification — §4.2 / §8.3; password reset — §4.3 / §8.4;
 * account settings + delete — §4.4 / §8.5 / §8.6; admin service accounts — §4.6.
 */

export const tokenPairSchema = z.object({
  access_token: z.string(),
  // Absent in cookie mode (ADR-18): Barrin's Identity puts the refresh token
  // in an HttpOnly cookie and drops it from the body
  // (`response_model_exclude_none`). Body mode still carries a string.
  refresh_token: z.string().nullish(),
  token_type: z.string(),
})
export type TokenPair = z.infer<typeof tokenPairSchema>

// Mirrors `UserRole` in `apps/barrins_identity/app/models/user.py`.
export const userRoleSchema = z.enum(['user', 'moderator', 'ml_developer', 'admin'])
export type UserRole = z.infer<typeof userRoleSchema>

/** `GET /api/v1/auth/me` → `UserRead`. */
export const principalSchema = z.object({
  id: z.uuid(),
  email: z.email(),
  username: z.string(),
  role: userRoleSchema,
  is_active: z.boolean(),
  is_verified: z.boolean(),
  display_name: z.string().nullable(),
})
export type Principal = z.infer<typeof principalSchema>

/**
 * `POST /api/v1/auth/signup` → `SignupResponse`. Branch on
 * `verification_required`, never on server config: `true` ⇒ `tokens` is
 * `null`, call `/signup/verify` next; `false` ⇒ `tokens` present, already
 * signed in.
 */
export const signupResponseSchema = z.object({
  detail: z.string(),
  verification_required: z.boolean(),
  tokens: tokenPairSchema.nullable(),
})
export type SignupResponse = z.infer<typeof signupResponseSchema>

/** `POST /api/v1/auth/signup/resend` → `ResendVerificationResponse` (always generic). */
export const resendVerificationResponseSchema = z.object({
  detail: z.string(),
})
export type ResendVerificationResponse = z.infer<typeof resendVerificationResponseSchema>

/**
 * `POST /api/v1/auth/password-reset/request` → `PasswordResetRequestResponse`.
 * Always the same generic body (§5 anti-enumeration) — never confirms whether
 * an account exists. `/password-reset/confirm` returns a `TokenPair`.
 */
export const passwordResetRequestResponseSchema = z.object({
  detail: z.string(),
})
export type PasswordResetRequestResponse = z.infer<
  typeof passwordResetRequestResponseSchema
>

/**
 * `POST /api/v1/users/me/email-change/resend` → `EmailChangeResendResponse`.
 * The caller is already authenticated, so — unlike the signup resend — this
 * message is specific rather than anti-enumeration generic. `PATCH
 * /api/v1/users/me` and `/users/me/email-change/verify` both return the
 * existing `principalSchema`.
 */
export const emailChangeResendResponseSchema = z.object({
  detail: z.string(),
})
export type EmailChangeResendResponse = z.infer<typeof emailChangeResendResponseSchema>

/**
 * `GET /api/v1/service-accounts` → `ServiceAccountRead`. The list contains
 * revoked accounts too (`is_active: false`) — the service keeps them for the
 * audit trail. Never carries a secret.
 */
export const serviceAccountSchema = z.object({
  id: z.uuid(),
  client_id: z.string(),
  description: z.string().nullable(),
  scopes: z.array(z.string()),
  is_active: z.boolean(),
  created_at: z.string(),
})
export type ServiceAccount = z.infer<typeof serviceAccountSchema>

export const serviceAccountListSchema = z.array(serviceAccountSchema)

/**
 * `POST /api/v1/service-accounts` → `ServiceAccountCreated`. Same shape as
 * {@link serviceAccountSchema} plus the plaintext `client_secret`, which the
 * service returns exactly once, at creation time.
 */
export const serviceAccountCreatedSchema = serviceAccountSchema.extend({
  client_secret: z.string(),
})
export type ServiceAccountCreated = z.infer<typeof serviceAccountCreatedSchema>

/**
 * `GET /api/v1/applications` → one card of the role-aware app directory
 * (ADR-19). `access` is computed by the backend for the caller — the SPA
 * only renders it (constitution §4.1):
 * - `open` — can be opened now;
 * - `login_required` — a members app the caller must sign in for;
 * - `role_denied` — signed in, but role below `min_role`.
 *
 * `logo_svg` is inline SVG markup served from the identity DB; render it as
 * an `<img>` data URI (an `<img>`-loaded SVG can't run scripts), never with
 * `dangerouslySetInnerHTML`. `min_role` is null unless the app is
 * role-restricted.
 */
export const applicationAccessSchema = z.enum(['open', 'login_required', 'role_denied'])
export type ApplicationAccess = z.infer<typeof applicationAccessSchema>

export const applicationSchema = z.object({
  key: z.string(),
  name: z.string(),
  description: z.string(),
  url: z.string(),
  logo_svg: z.string(),
  access: applicationAccessSchema,
  min_role: userRoleSchema.nullable(),
})
export type Application = z.infer<typeof applicationSchema>

export const applicationListSchema = z.array(applicationSchema)
