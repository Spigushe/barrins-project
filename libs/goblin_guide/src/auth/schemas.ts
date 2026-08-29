import { z } from 'zod'

/**
 * Wire shapes for the Barrin's Identity endpoints Goblin Guide consumes.
 * Only the login slice is covered so far — see
 * `docs/content/back/barrins_identity/integration.md` §4.1.
 */

export const tokenPairSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
})
export type TokenPair = z.infer<typeof tokenPairSchema>

export const userRoleSchema = z.enum(['user', 'placeholder', 'ml_developer', 'admin'])
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
