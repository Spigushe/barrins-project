import { z } from 'zod'
import {
  detailResponseSchema,
  signupResponseSchema,
  tokenPairSchema,
  userSchema,
} from '@/schemas/auth'
import { API_BASE_URL, ApiError, apiRequest, parseErrorMessage } from './client'

export async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email, password }),
  })
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response))
  }
  return tokenPairSchema.parse(await response.json())
}

export function signup(email: string, password: string, displayName?: string) {
  return apiRequest('/api/v1/auth/signup', signupResponseSchema, {
    method: 'POST',
    body: { email, password, display_name: displayName },
    requireAuth: false,
  })
}

export function verifyEmail(email: string, code: string) {
  return apiRequest('/api/v1/auth/signup/verify', tokenPairSchema, {
    method: 'POST',
    body: { email, code },
    requireAuth: false,
  })
}

export function resendVerification(email: string) {
  return apiRequest('/api/v1/auth/signup/resend', detailResponseSchema, {
    method: 'POST',
    body: { email },
    requireAuth: false,
  })
}

export function getMe() {
  return apiRequest('/api/v1/auth/me', userSchema)
}

export function logout() {
  return apiRequest('/api/v1/auth/logout', z.void(), { method: 'POST' })
}
