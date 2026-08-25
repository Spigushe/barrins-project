import { z, type ZodType } from 'zod'

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

// `/bff/tolaria-news/*` has no `CurrentUser` on any route (T4, enforced by
// its own `TestNoAuthRequired` suite) — this client never sends an
// `Authorization` header and has no session/refresh logic to manage.
type QueryParams = Record<string, string | number | boolean | string[] | undefined>

export interface RequestConfig {
  params?: QueryParams
}

function buildUrl(path: string, config: RequestConfig): URL {
  const url = new URL(`${API_BASE_URL}${path}`)
  for (const [key, value] of Object.entries(config.params ?? {})) {
    if (value === undefined) continue
    // Array values serialize as repeated keys (`?colors=W&colors=U`),
    // matching FastAPI's `Query(list[str])` list-param convention.
    if (Array.isArray(value)) {
      for (const item of value) url.searchParams.append(key, item)
    } else {
      url.searchParams.set(key, String(value))
    }
  }
  return url
}

export const metaSchema = z.object({
  generated_at: z.iso.datetime({ offset: true }),
  source_synced_at: z.iso.datetime({ offset: true }).nullable(),
})
export type Meta = z.infer<typeof metaSchema>

export const pageSchema = z.object({
  next_cursor: z.string().nullable(),
  limit: z.number(),
})
export type Page = z.infer<typeof pageSchema>

export interface Envelope<T> {
  data: T
  meta: Meta
  page: Page | null
}

/** Matches `app.schemas.responses_tolaria_news.Envelope` (`{data, meta, page?}`). */
function envelopeSchema<T extends ZodType>(dataSchema: T) {
  return z.object({
    data: dataSchema,
    meta: metaSchema,
    page: pageSchema.nullable().optional(),
  })
}

export async function apiRequest<T>(
  path: string,
  dataSchema: ZodType<T>,
  config: RequestConfig = {},
): Promise<Envelope<T>> {
  const url = buildUrl(path, config)
  const response = await fetch(url.toString())

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorMessage(response))
  }

  const parsed = envelopeSchema(dataSchema).parse(await response.json())
  return { data: parsed.data, meta: parsed.meta, page: parsed.page ?? null }
}
