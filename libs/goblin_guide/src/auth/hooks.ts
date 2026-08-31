import { useSyncExternalStore } from 'react'
import {
  useMutation,
  type UseMutationResult,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query'
import type { AccountUpdateInput, ServiceAccountCreateInput, SignupInput } from './client'
import { useIdentityContext } from './context'
import type {
  Application,
  EmailChangeResendResponse,
  PasswordResetRequestResponse,
  Principal,
  ResendVerificationResponse,
  ServiceAccount,
  ServiceAccountCreated,
  SignupResponse,
  TokenPair,
} from './schemas'

const ME_QUERY_KEY = ['goblin-guide', 'me'] as const
const APPLICATIONS_QUERY_KEY = ['goblin-guide', 'applications'] as const
const SERVICE_ACCOUNTS_QUERY_KEY = ['goblin-guide', 'service-accounts'] as const

/** Reactive authentication state, derived from the token store. */
export function useIdentity(): { isAuthenticated: boolean } {
  const { tokenStore } = useIdentityContext()
  const access = useSyncExternalStore(
    tokenStore.subscribe,
    tokenStore.getAccess,
    tokenStore.getAccess,
  )
  return { isAuthenticated: access !== null }
}

/** `GET /api/v1/auth/me`, enabled once there is an access token. */
export function useCurrentUser(): UseQueryResult<Principal> {
  const { client } = useIdentityContext()
  const { isAuthenticated } = useIdentity()
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: () => client.me(),
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  })
}

export interface LoginVariables {
  email: string
  password: string
}

/** `POST /api/v1/auth/token`. On success the token store is populated. */
export function useLogin(): UseMutationResult<unknown, Error, LoginVariables> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ email, password }: LoginVariables) => client.login(email, password),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
    },
  })
}

/** `POST /api/v1/auth/logout`. Clears cached queries once settled. */
export function useLogout(): UseMutationResult<void, Error, void> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => client.logout(),
    onSettled: () => {
      queryClient.clear()
    },
  })
}

/**
 * `POST /api/v1/auth/signup`. When the server returns tokens (email
 * verification disabled) the store is populated and the `me` query refreshed;
 * otherwise the caller routes to the verification step.
 */
export function useSignup(): UseMutationResult<SignupResponse, Error, SignupInput> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: SignupInput) => client.signup(input),
    onSuccess: (result) => {
      if (result.tokens !== null) {
        void queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
      }
    },
  })
}

export interface VerifyEmailVariables {
  email: string
  code: string
}

/** `POST /api/v1/auth/signup/verify`. On success the token store is populated. */
export function useVerifyEmail(): UseMutationResult<
  TokenPair,
  Error,
  VerifyEmailVariables
> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ email, code }: VerifyEmailVariables) =>
      client.verifyEmail(email, code),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
    },
  })
}

/** `POST /api/v1/auth/signup/resend`. Response is always the same generic body. */
export function useResendVerification(): UseMutationResult<
  ResendVerificationResponse,
  Error,
  string
> {
  const { client } = useIdentityContext()
  return useMutation({
    mutationFn: (email: string) => client.resendVerification(email),
  })
}

/**
 * `POST /api/v1/auth/password-reset/request`. Response is always the same
 * generic body (§5) — it never confirms whether an account exists.
 */
export function usePasswordResetRequest(): UseMutationResult<
  PasswordResetRequestResponse,
  Error,
  string
> {
  const { client } = useIdentityContext()
  return useMutation({
    mutationFn: (email: string) => client.requestPasswordReset(email),
  })
}

export interface PasswordResetConfirmVariables {
  email: string
  code: string
  newPassword: string
}

/**
 * `POST /api/v1/auth/password-reset/confirm`. On success the token store is
 * populated with a fresh pair (every other session for the account is revoked).
 */
export function usePasswordResetConfirm(): UseMutationResult<
  TokenPair,
  Error,
  PasswordResetConfirmVariables
> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ email, code, newPassword }: PasswordResetConfirmVariables) =>
      client.confirmPasswordReset(email, code, newPassword),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
    },
  })
}

/** `PATCH /api/v1/users/me`. Refreshes `me` on success. */
export function useUpdateAccount(): UseMutationResult<
  Principal,
  Error,
  AccountUpdateInput
> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: AccountUpdateInput) => client.updateAccount(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
    },
  })
}

/** `POST /api/v1/users/me/email-change/verify`. Refreshes `me` on success. */
export function useVerifyEmailChange(): UseMutationResult<Principal, Error, string> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (code: string) => client.verifyEmailChange(code),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
    },
  })
}

/** `POST /api/v1/users/me/email-change/resend`. */
export function useResendEmailChange(): UseMutationResult<
  EmailChangeResendResponse,
  Error,
  void
> {
  const { client } = useIdentityContext()
  return useMutation({
    mutationFn: () => client.resendEmailChange(),
  })
}

/**
 * `DELETE /api/v1/users/me`. On success the client has already cleared local
 * token state; this drops every cached query so the app falls back to the
 * login screen. A failed attempt (e.g. wrong password) leaves the cache
 * untouched so the confirmation form stays put.
 */
export function useDeleteAccount(): UseMutationResult<void, Error, string> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (currentPassword: string) => client.deleteAccount(currentPassword),
    onSuccess: () => {
      queryClient.clear()
    },
  })
}

/**
 * `GET /api/v1/applications` — the role-aware app directory (ADR-19).
 * Always enabled: it works signed out, and re-runs when the session
 * changes so `access` badges stay right after login/logout.
 */
export function useApplications(): UseQueryResult<Application[]> {
  const { client } = useIdentityContext()
  const { isAuthenticated } = useIdentity()
  return useQuery({
    queryKey: [...APPLICATIONS_QUERY_KEY, { authed: isAuthenticated }],
    queryFn: () => client.listApplications(),
    staleTime: 5 * 60_000,
  })
}

/**
 * `GET /api/v1/service-accounts` (admin). Enabled once authenticated — the
 * caller is expected to render this only for an `admin` principal (a
 * non-admin request comes back `403`).
 */
export function useServiceAccounts(): UseQueryResult<ServiceAccount[]> {
  const { client } = useIdentityContext()
  const { isAuthenticated } = useIdentity()
  return useQuery({
    queryKey: SERVICE_ACCOUNTS_QUERY_KEY,
    queryFn: () => client.listServiceAccounts(),
    enabled: isAuthenticated,
  })
}

/** `POST /api/v1/service-accounts` (admin). Refreshes the list on success. */
export function useCreateServiceAccount(): UseMutationResult<
  ServiceAccountCreated,
  Error,
  ServiceAccountCreateInput
> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ServiceAccountCreateInput) => client.createServiceAccount(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SERVICE_ACCOUNTS_QUERY_KEY })
    },
  })
}

/**
 * `POST /api/v1/service-accounts/{client_id}/revoke` (admin). Refreshes the
 * list on success — the revoked account stays in it, now `is_active: false`.
 */
export function useRevokeServiceAccount(): UseMutationResult<void, Error, string> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (clientId: string) => client.revokeServiceAccount(clientId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SERVICE_ACCOUNTS_QUERY_KEY })
    },
  })
}
