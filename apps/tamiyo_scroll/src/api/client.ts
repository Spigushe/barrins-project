import type { ZodType } from 'zod'
import { tokenPairSchema } from '@/schemas/auth'
import { clearSession, sessionStore, setSession } from './session'
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
    return data.error?.message ?? data.detail ?? `Erreur ${response.status.toString()}`
  } catch {
    return `Erreur ${response.status.toString()}`
  }
}

// Une seule tentative de refresh en vol — les requêtes concurrentes qui
// reçoivent un 401 pendant le refresh attendent la même promesse.
let refreshPromise: Promise<void> | null = null

async function performRefresh(): Promise<void> {
  const { refreshToken } = sessionStore.get()
  if (!refreshToken) {
    clearSession()
    throw new ApiError(401, 'Session expirée.')
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) {
    clearSession()
    throw new ApiError(401, 'Session expirée.')
  }
  setSession(tokenPairSchema.parse(await response.json()))
}

type QueryParams = Record<string, string | number | boolean | undefined>

export interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  params?: QueryParams
  /**
   * Applique automatiquement `owner_id` (vue partagée) — GET uniquement.
   * Ne jamais activer sur une mutation : cf.
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

export async function apiRequest<T>(
  path: string,
  schema: ZodType<T>,
  config: RequestConfig = {},
): Promise<T> {
  const { method = 'GET', body, requireAuth = true } = config
  const url = buildUrl(path, config)

  const doFetch = (): Promise<Response> => {
    const headers: Record<string, string> = {}
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    if (requireAuth) {
      const { accessToken } = sessionStore.get()
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

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return schema.parse(await response.json())
}
