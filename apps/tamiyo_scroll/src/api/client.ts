import type { ZodType } from 'zod'
import { identityClient, identityTokenStore } from '@/identity'
import { viewingOwnerStore } from './viewingOwner'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL as string

export class ApiError extends Error {
  status: number
  details?: unknown

  constructor(status: number, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

export async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as {
      error?: { message?: string }
      detail?: string
    }
    return data.error?.message ?? data.detail ?? `Error ${response.status.toString()}`
  } catch {
    return `Error ${response.status.toString()}`
  }
}

// Only one refresh attempt in flight — concurrent requests that get a 401
// during the refresh await the same promise. `identityClient.refresh()`
// trades the identity refresh cookie (ADR-18) for a fresh access token and
// writes it into `identityTokenStore`; on failure it clears the store and
// throws, which we surface as a 401 `ApiError`.
let refreshPromise: Promise<void> | null = null

async function performRefresh(): Promise<void> {
  try {
    await identityClient.refresh()
  } catch {
    throw new ApiError(401, 'Session expired.')
  }
}

type QueryParams = Record<string, string | number | boolean | undefined>

export interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  params?: QueryParams
  /**
   * Automatically applies `owner_id` (shared view) — GET only.
   * Never enable on a mutation: see
   * barrins_api/docs/tamiyo_scroll_tracker/00_plan_general.md, Option B.
   */
  applyOwnerParam?: boolean
  requireAuth?: boolean
}

function buildUrl(path: string, config: RequestConfig): URL {
  const url = new URL(`${API_BASE_URL}${path}`)
  for (const [key, value] of Object.entries(config.params ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value))
  }
  if (config.applyOwnerParam && (config.method ?? 'GET') === 'GET') {
    const owner = viewingOwnerStore.get()
    if (owner) url.searchParams.set('owner_id', owner.id)
  }
  return url
}

async function fetchWithAuthRetry(path: string, config: RequestConfig): Promise<Response> {
  const { method = 'GET', body, requireAuth = true } = config
  const url = buildUrl(path, config)

  const doFetch = (): Promise<Response> => {
    const headers: Record<string, string> = {}
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    if (requireAuth) {
      const accessToken = identityTokenStore.getAccess()
      if (accessToken) headers.Authorization = `Bearer ${accessToken}`
    }
    return fetch(url.toString(), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  }

  let response = await doFetch()

  if (response.status === 401 && requireAuth) {
    refreshPromise ??= performRefresh().finally(() => {
      refreshPromise = null
    })
    try {
      await refreshPromise
    } catch (err) {
      window.location.assign('/login')
      throw err
    }
    response = await doFetch()
  }

  return response
}

export async function apiRequest<T>(
  path: string,
  schema: ZodType<T>,
  config: RequestConfig = {},
): Promise<T> {
  const response = await fetchWithAuthRetry(path, config)

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return schema.parse(await response.json())
}

/** Like `apiRequest`, but for binary responses (e.g. a PDF download) — no JSON parsing. */
export async function apiRequestBlob(
  path: string,
  config: RequestConfig = {},
): Promise<Blob> {
  const response = await fetchWithAuthRetry(path, config)

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response))
  }

  return response.blob()
}
