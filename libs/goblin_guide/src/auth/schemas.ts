import { z } from 'zod'

/**
 * Wire shapes for the Barrin's Identity endpoints Goblin Guide consumes.
 * Login slice — see `docs/content/back/barrins_identity/integration.md` §4.1;
 * signup + email verification — §4.2 / §8.3.
 */

export const tokenPairSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
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
