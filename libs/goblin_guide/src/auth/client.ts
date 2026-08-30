import {
  type EmailChangeResendResponse,
  emailChangeResendResponseSchema,
  type PasswordResetRequestResponse,
  passwordResetRequestResponseSchema,
  type Principal,
  principalSchema,
  type ResendVerificationResponse,
  resendVerificationResponseSchema,
  type ServiceAccount,
  type ServiceAccountCreated,
  serviceAccountCreatedSchema,
  serviceAccountListSchema,
  type SignupResponse,
  signupResponseSchema,
  type TokenPair,
  tokenPairSchema,
} from './schemas'
import type { TokenStore } from './tokenStore'

/** A `4xx`/`5xx` from Barrin's Identity, carrying the parsed message. */
export class IdentityError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'IdentityError'
    this.status = status
  }
}

/**
 * The subset of `fetch` this client uses — it only ever passes string URLs.
 * The global `fetch` is assignable to this, and so are simple test doubles.
 */
export type FetchLike = (url: string, init?: RequestInit) => Promise<Response>

/** Fields the signup form collects (`POST /api/v1/auth/signup`). */
export interface SignupInput {
  email: string
  username: string
  password: string
  displayName?: string
}

/**
 * Partial update for `PATCH /api/v1/users/me`. A field left `undefined` is
 * omitted from the request (server leaves it untouched); `displayName: null`
 * clears the display name.
 */
export interface AccountUpdateInput {
  displayName?: string | null
  email?: string
}

/** Body for `POST /api/v1/service-accounts` (admin-only). */
export interface ServiceAccountCreateInput {
  /** Free-text label shown in the list; omitted from the request when `undefined`. */
  description?: string | null
  /** At least one opaque scope string — the service rejects an empty list. */
  scopes: string[]
}

async function readDetail(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as {
      detail?: unknown
      error?: { message?: unknown }
    }
    // Barrin's Identity wraps raised errors as `{"error": {"message", ...}}`
    // (`app/core/error_handlers.py`); older services use a bare `detail`.
    if (typeof data.error?.message === 'string') return data.error.message
    if (typeof data.detail === 'string') return data.detail
  } catch {
    // fall through to the generic message
  }
  return `Request failed (${String(response.status)}).`
}

export interface IdentityClient {
  /** `POST /api/v1/auth/token` — exchange email + password for a token pair. */
  login: (email: string, password: string) => Promise<TokenPair>
  /** `POST /api/v1/auth/refresh` — rotate the pair using the stored refresh token. */
  refresh: () => Promise<TokenPair>
  /** `GET /api/v1/auth/me` — the current principal (silent-refresh aware). */
  me: () => Promise<Principal>
  /** `POST /api/v1/auth/logout` — best-effort; local token state is cleared regardless. */
  logout: () => Promise<void>
  /**
   * `POST /api/v1/auth/signup` — self-registration. When the response carries
   * `tokens` (email verification disabled server-side) they are stored.
   */
  signup: (input: SignupInput) => Promise<SignupResponse>
  /** `POST /api/v1/auth/signup/verify` — submit the emailed code; stores the pair. */
  verifyEmail: (email: string, code: string) => Promise<TokenPair>
  /** `POST /api/v1/auth/signup/resend` — re-send the code (server enforces a cooldown). */
  resendVerification: (email: string) => Promise<ResendVerificationResponse>
  /**
   * `POST /api/v1/auth/password-reset/request` — ask for a reset code. The
   * response is always the same generic body; the server enforces a cooldown.
   */
  requestPasswordReset: (email: string) => Promise<PasswordResetRequestResponse>
  /**
   * `POST /api/v1/auth/password-reset/confirm` — submit the code + new password.
   * Stores the returned pair; every previously issued token for the account is
   * invalidated server-side (`token_version` bump), so this is a fresh login.
   */
  confirmPasswordReset: (
    email: string,
    code: string,
    newPassword: string,
  ) => Promise<TokenPair>
  /**
   * `PATCH /api/v1/users/me` — update the caller's profile. `displayName`
   * maps to `display_name` (`null` clears it); a new `email` starts an
   * email-change: while the server requires email verification the response
   * still carries the *old* address and a code is sent to the new one.
   * `409` (email taken) / `502` (code send failed) → `IdentityError`.
   */
  updateAccount: (input: AccountUpdateInput) => Promise<Principal>
  /**
   * `POST /api/v1/users/me/email-change/verify` — confirm a pending email
   * change with its 6-digit code. Resolves to the principal with the new
   * email; existing tokens keep working.
   */
  verifyEmailChange: (code: string) => Promise<Principal>
  /**
   * `POST /api/v1/users/me/email-change/resend` — re-send the pending code.
   * The server enforces a cooldown and returns the same body regardless.
   */
  resendEmailChange: () => Promise<EmailChangeResendResponse>
  /**
   * `DELETE /api/v1/users/me` — soft-delete the account, re-authenticating
   * with the current password. Clears local token state on success; every
   * token for the account is invalidated server-side. `401` (wrong
   * password) → `IdentityError`.
   */
  deleteAccount: (currentPassword: string) => Promise<void>
  /**
   * `GET /api/v1/service-accounts` — every service account, revoked ones
   * included. Admin only (`403` for anyone else). Never carries a secret.
   */
  listServiceAccounts: () => Promise<ServiceAccount[]>
  /**
   * `POST /api/v1/service-accounts` — create one. Admin only. The response
   * carries the plaintext `client_secret` once and only once.
   */
  createServiceAccount: (
    input: ServiceAccountCreateInput,
  ) => Promise<ServiceAccountCreated>
  /**
   * `POST /api/v1/service-accounts/{client_id}/revoke` — deactivate an
   * account and reject its outstanding tokens. Admin only. Resolves on the
   * `204`; `404` (unknown `client_id`) → `IdentityError`.
   */
  revokeServiceAccount: (clientId: string) => Promise<void>
}

export interface IdentityClientOptions {
  /** Base URL of the Barrin's Identity service (no trailing slash needed). */
  serviceUrl: string
  tokenStore: TokenStore
  /** Injectable for tests; defaults to the global `fetch`. */
  fetchImpl?: FetchLike
}

export function createIdentityClient(options: IdentityClientOptions): IdentityClient {
  const { tokenStore } = options
  const doFetch: FetchLike =
    options.fetchImpl ?? ((url, init) => globalThis.fetch(url, init))
  const base = options.serviceUrl.replace(/\/+$/, '')

  // Only one refresh in flight — concurrent 401s await the same promise.
  let refreshInFlight: Promise<TokenPair> | null = null

  async function refresh(): Promise<TokenPair> {
    const refreshToken = tokenStore.getRefresh()
    if (refreshToken === null) {
      tokenStore.clear()
      throw new IdentityError(401, 'Your session has ended. Please sign in again.')
    }
    const response = await doFetch(`${base}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) {
      tokenStore.clear()
      throw new IdentityError(401, 'Your session has ended. Please sign in again.')
    }
    const pair = tokenPairSchema.parse(await response.json())
    tokenStore.set(pair)
    return pair
  }

  function refreshOnce(): Promise<TokenPair> {
    refreshInFlight ??= refresh().finally(() => {
      refreshInFlight = null
    })
    return refreshInFlight
  }

  /** Authenticated request with a single silent-refresh retry on `401`. */
  async function authed(path: string, init: RequestInit = {}): Promise<Response> {
    const send = (): Promise<Response> => {
      const access = tokenStore.getAccess()
      const headers = new Headers(init.headers)
      if (access !== null) headers.set('Authorization', `Bearer ${access}`)
      return doFetch(`${base}${path}`, { ...init, headers })
    }

    const first = await send()
    if (first.status !== 401) return first

    await refreshOnce()
    return send()
  }

  /** `authed`, plus a JSON body and `Content-Type` header. */
  function authedJson(path: string, method: string, body: unknown): Promise<Response> {
    return authed(path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  }

  async function login(email: string, password: string): Promise<TokenPair> {
    const response = await doFetch(`${base}/api/v1/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      // The OAuth2 form field is named `username`; it carries the email
      // (login by handle — `Q-05` — is deferred).
      body: new URLSearchParams({ username: email, password }),
    })
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    const pair = tokenPairSchema.parse(await response.json())
    tokenStore.set(pair)
    return pair
  }

  async function me(): Promise<Principal> {
    const response = await authed('/api/v1/auth/me')
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    return principalSchema.parse(await response.json())
  }

  async function logout(): Promise<void> {
    try {
      await authed('/api/v1/auth/logout', { method: 'POST' })
    } catch {
      // The server-side `token_version` bump on logout is best-effort from
      // the client's side — clearing local state below is what signs the
      // user out of this tab.
    } finally {
      tokenStore.clear()
    }
  }

  function postJson(path: string, body: unknown): Promise<Response> {
    return doFetch(`${base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  }

  async function signup(input: SignupInput): Promise<SignupResponse> {
    const body: Record<string, string> = {
      email: input.email,
      username: input.username,
      password: input.password,
    }
    if (input.displayName !== undefined) body.display_name = input.displayName
    const response = await postJson('/api/v1/auth/signup', body)
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    const result = signupResponseSchema.parse(await response.json())
    if (result.tokens !== null) tokenStore.set(result.tokens)
    return result
  }

  async function verifyEmail(email: string, code: string): Promise<TokenPair> {
    const response = await postJson('/api/v1/auth/signup/verify', { email, code })
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    const pair = tokenPairSchema.parse(await response.json())
    tokenStore.set(pair)
    return pair
  }

  async function resendVerification(email: string): Promise<ResendVerificationResponse> {
    const response = await postJson('/api/v1/auth/signup/resend', { email })
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    return resendVerificationResponseSchema.parse(await response.json())
  }

  async function requestPasswordReset(
    email: string,
  ): Promise<PasswordResetRequestResponse> {
    const response = await postJson('/api/v1/auth/password-reset/request', { email })
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    return passwordResetRequestResponseSchema.parse(await response.json())
  }

  async function confirmPasswordReset(
    email: string,
    code: string,
    newPassword: string,
  ): Promise<TokenPair> {
    const response = await postJson('/api/v1/auth/password-reset/confirm', {
      email,
      code,
      new_password: newPassword,
    })
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    const pair = tokenPairSchema.parse(await response.json())
    tokenStore.set(pair)
    return pair
  }

  async function updateAccount(input: AccountUpdateInput): Promise<Principal> {
    const body: Record<string, unknown> = {}
    if (input.displayName !== undefined) body.display_name = input.displayName
    if (input.email !== undefined) body.email = input.email
    const response = await authedJson('/api/v1/users/me', 'PATCH', body)
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    return principalSchema.parse(await response.json())
  }

  async function verifyEmailChange(code: string): Promise<Principal> {
    const response = await authedJson('/api/v1/users/me/email-change/verify', 'POST', {
      code,
    })
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    return principalSchema.parse(await response.json())
  }

  async function resendEmailChange(): Promise<EmailChangeResendResponse> {
    const response = await authed('/api/v1/users/me/email-change/resend', {
      method: 'POST',
    })
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    return emailChangeResendResponseSchema.parse(await response.json())
  }

  async function deleteAccount(currentPassword: string): Promise<void> {
    const response = await authedJson('/api/v1/users/me', 'DELETE', {
      current_password: currentPassword,
    })
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    // Every token for the account is invalidated server-side; drop ours too.
    tokenStore.clear()
  }

  async function listServiceAccounts(): Promise<ServiceAccount[]> {
    const response = await authed('/api/v1/service-accounts')
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    return serviceAccountListSchema.parse(await response.json())
  }

  async function createServiceAccount(
    input: ServiceAccountCreateInput,
  ): Promise<ServiceAccountCreated> {
    const body: Record<string, unknown> = { scopes: input.scopes }
    if (input.description !== undefined) body.description = input.description
    const response = await authedJson('/api/v1/service-accounts', 'POST', body)
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
    return serviceAccountCreatedSchema.parse(await response.json())
  }

  async function revokeServiceAccount(clientId: string): Promise<void> {
    const response = await authed(
      `/api/v1/service-accounts/${encodeURIComponent(clientId)}/revoke`,
      { method: 'POST' },
    )
    if (!response.ok) {
      throw new IdentityError(response.status, await readDetail(response))
    }
  }

  return {
    login,
    refresh,
    me,
    logout,
    signup,
    verifyEmail,
    resendVerification,
    requestPasswordReset,
    confirmPasswordReset,
    updateAccount,
    verifyEmailChange,
    resendEmailChange,
    deleteAccount,
    listServiceAccounts,
    createServiceAccount,
    revokeServiceAccount,
  }
}
