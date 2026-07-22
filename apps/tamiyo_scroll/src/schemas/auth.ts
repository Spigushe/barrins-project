import { z } from 'zod'

export const userRoleSchema = z.enum(['user', 'placeholder', 'ml_developer', 'admin'])

export const userSchema = z.object({
  id: z.uuid(),
  email: z.email(),
  role: userRoleSchema,
  is_active: z.boolean(),
  is_verified: z.boolean(),
  display_name: z.string().nullable(),
})
export type User = z.infer<typeof userSchema>

export const tokenPairSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
})
export type TokenPair = z.infer<typeof tokenPairSchema>

export const detailResponseSchema = z.object({ detail: z.string() })

export const signupResponseSchema = z.object({
  detail: z.string(),
  verification_required: z.boolean(),
  tokens: tokenPairSchema.nullable(),
})
export type SignupResponse = z.infer<typeof signupResponseSchema>
