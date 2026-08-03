import type {
  ArchetypeCategory,
  CardGame,
  CardTestWrite,
  MatchWrite,
  MetaDeckWrite,
  SessionCreate,
  SessionPatch,
} from '@/schemas/tamiyoScroll'
import * as cardTestsDemo from './api/cardTests'
import * as matchesDemo from './api/matches'
import * as metaDecksDemo from './api/metaDecks'
import * as personalDecksDemo from './api/personalDecks'
import * as sessionsDemo from './api/sessions'
import * as statsDemo from './api/stats'
import * as teamsDemo from './api/teams'

/**
 * The seam that lets `MetagameTab`/`SuiviBo3Tab`/`DecklistTab` — and every
 * hook and `src/api/*.ts` function they call — run completely unmodified in
 * demo mode.
 *
 * `usePersonalDecks`, `useMatches`, etc. all funnel through `apiRequest` /
 * `apiRequestBlob` in `src/api/client.ts`, which ultimately call the global
 * `fetch`. Rather than editing those hooks or the `api/*.ts` modules to
 * branch on "am I in demo mode", `DemoModeProvider` swaps `window.fetch`
 * itself for the lifetime of the demo page. Every request the real code path
 * would have sent to `barrins_api` is instead routed here, in-process, to
 * the demo data-source module in `./api/` — so no network call is ever
 * made (this is also why "no calls to barrins_api" is structural rather
 * than a promise: there is no fallback to the original `fetch` below).
 *
 * This mirrors a technique already used in this codebase's own tests
 * (`src/api/__tests__/client.test.ts` uses `vi.stubGlobal('fetch', ...)`).
 */

const BASE = '/bff/tamiyo-scroll'

interface RouteContext {
  params: string[]
  searchParams: URLSearchParams
  body: unknown
}

interface Route {
  method: string
  pattern: RegExp
  handler: (ctx: RouteContext) => Promise<unknown>
  /** The result is already a Blob (e.g. a PDF download) — don't JSON-encode it. */
  isBlob?: boolean
}

const routes: Route[] = [
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/personal-decks$`),
    handler: ({ searchParams }) =>
      personalDecksDemo.listPersonalDecks({
        includeArchived: searchParams.get('include_archived') === 'true',
      }),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/personal-decks$`),
    handler: ({ body }) =>
      personalDecksDemo.createPersonalDeck(
        body as { name: string; game: CardGame; category: ArchetypeCategory },
      ),
  },
  {
    method: 'PATCH',
    pattern: new RegExp(`^${BASE}/personal-decks/([^/]+)$`),
    handler: ({ params, body }) =>
      personalDecksDemo.updatePersonalDeck(
        params[0],
        body as { name?: string; game?: CardGame; category?: ArchetypeCategory },
      ),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/personal-decks/([^/]+)$`),
    handler: ({ params }) => personalDecksDemo.archivePersonalDeck(params[0]),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/personal-decks/([^/]+)/versions$`),
    handler: ({ params }) => personalDecksDemo.listDecklistVersions(params[0]),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/personal-decks/([^/]+)/versions/import-moxfield$`),
    handler: ({ params, body }) =>
      personalDecksDemo.importMoxfield(
        params[0],
        (body as { moxfield_url: string }).moxfield_url,
      ),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/personal-decks/([^/]+)/versions$`),
    handler: ({ params, body }) =>
      personalDecksDemo.createDecklistVersion(
        params[0],
        (body as { content: string }).content,
      ),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/personal-decks/([^/]+)/versions/([^/]+)$`),
    handler: ({ params }) =>
      personalDecksDemo.deleteDecklistVersion(params[0], params[1]),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/personal-decks/([^/]+)/decklist-view$`),
    handler: ({ params }) => personalDecksDemo.getDecklistView(params[0]),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/personal-decks/([^/]+)/report\\.pdf$`),
    handler: ({ params }) => personalDecksDemo.getDeckReportPdf(params[0]),
    isBlob: true,
  },

  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/meta-decks$`),
    handler: ({ searchParams }) =>
      metaDecksDemo.listMetaDecks({
        includeArchived: searchParams.get('include_archived') === 'true',
      }),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/meta-decks$`),
    handler: ({ body }) => metaDecksDemo.createMetaDeck(body as MetaDeckWrite),
  },
  {
    method: 'PUT',
    pattern: new RegExp(`^${BASE}/meta-decks/([^/]+)$`),
    handler: ({ params, body }) =>
      metaDecksDemo.updateMetaDeck(params[0], body as MetaDeckWrite),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/meta-decks/([^/]+)$`),
    handler: ({ params }) => metaDecksDemo.archiveMetaDeck(params[0]),
  },

  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/matches$`),
    handler: ({ searchParams }) =>
      matchesDemo.listMatches(searchParams.get('personal_deck_id') ?? ''),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/matches$`),
    handler: ({ body }) => matchesDemo.createMatch(body as MatchWrite),
  },
  {
    method: 'PUT',
    pattern: new RegExp(`^${BASE}/matches/([^/]+)$`),
    handler: ({ params, body }) => matchesDemo.updateMatch(params[0], body as MatchWrite),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/matches/([^/]+)$`),
    handler: ({ params }) => matchesDemo.deleteMatch(params[0]),
  },

  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/card-tests$`),
    handler: ({ searchParams }) =>
      cardTestsDemo.listCardTests({
        personalDeckId: searchParams.get('personal_deck_id') ?? undefined,
      }),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/card-tests$`),
    handler: ({ body }) => cardTestsDemo.createCardTest(body as CardTestWrite),
  },
  {
    method: 'PUT',
    pattern: new RegExp(`^${BASE}/card-tests/([^/]+)$`),
    handler: ({ params, body }) =>
      cardTestsDemo.updateCardTest(params[0], body as CardTestWrite),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/card-tests/([^/]+)$`),
    handler: ({ params }) => cardTestsDemo.deleteCardTest(params[0]),
  },

  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/archetype-summary$`),
    handler: ({ searchParams }) =>
      statsDemo.getArchetypeSummary({
        personalDeckId: searchParams.get('personal_deck_id') ?? undefined,
      }),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/matchup-summary$`),
    handler: ({ searchParams }) =>
      statsDemo.getMatchupSummary({
        personalDeckId: searchParams.get('personal_deck_id') ?? undefined,
      }),
  },

  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/sessions$`),
    handler: ({ searchParams }) =>
      sessionsDemo.listSessions(
        searchParams.get('personal_deck_id') ?? '',
        searchParams.get('include_archived') === 'true',
      ),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/sessions$`),
    handler: ({ body }) => sessionsDemo.createSession(body as SessionCreate),
  },
  {
    method: 'PATCH',
    pattern: new RegExp(`^${BASE}/sessions/([^/]+)$`),
    handler: ({ params, body }) =>
      sessionsDemo.updateSession(params[0], body as SessionPatch),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/sessions/([^/]+)$`),
    handler: ({ params }) => sessionsDemo.archiveSession(params[0]),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/sessions/([^/]+)/comparison$`),
    handler: ({ params }) => sessionsDemo.getSessionComparison(params[0]),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/sessions/([^/]+)/report\\.pdf$`),
    handler: ({ params }) => sessionsDemo.getSessionReportPdf(params[0]),
    isBlob: true,
  },

  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/teams/mine$`),
    handler: () => teamsDemo.listMyTeams(),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/teams$`),
    handler: ({ body }) => teamsDemo.createTeam((body as { name: string }).name),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/teams/join$`),
    handler: ({ body }) =>
      teamsDemo.joinTeam((body as { invite_code: string }).invite_code),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)$`),
    handler: ({ params }) => teamsDemo.getTeam(params[0]),
  },
  {
    method: 'PATCH',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)$`),
    handler: ({ params, body }) =>
      teamsDemo.updateTeamDescription(
        params[0],
        (body as { description: string | null }).description,
      ),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)$`),
    handler: ({ params, body }) =>
      teamsDemo.deleteTeam(params[0], (body as { invite_code: string }).invite_code),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/leave$`),
    handler: ({ params }) => teamsDemo.leaveTeam(params[0]),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/members/([^/]+)$`),
    handler: ({ params }) => teamsDemo.removeTeamMember(params[0], params[1]),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/decks$`),
    handler: ({ params }) => teamsDemo.listTeamDecks(params[0]),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/members/decks$`),
    handler: ({ params }) => teamsDemo.listMemberDecks(params[0]),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/decks/flags$`),
    handler: ({ params, body }) =>
      teamsDemo.flagTeamDeck(params[0], (body as { deck_id: string }).deck_id),
  },
  {
    method: 'DELETE',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/decks/flags/([^/]+)$`),
    handler: ({ params }) =>
      teamsDemo.unflagTeamDeck(params[0], decodeURIComponent(params[1])),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/decks/([^/]+)/report\\.pdf$`),
    handler: ({ params }) =>
      teamsDemo.getTeamDeckReportPdf(params[0], decodeURIComponent(params[1])),
    isBlob: true,
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/decks/([^/]+)/thread$`),
    handler: ({ params }) =>
      teamsDemo.enableTeamDeckThread(params[0], decodeURIComponent(params[1])),
  },
  {
    method: 'GET',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/decks/([^/]+)/thread/messages$`),
    handler: ({ params }) =>
      teamsDemo.listTeamDeckThreadMessages(params[0], decodeURIComponent(params[1])),
  },
  {
    method: 'POST',
    pattern: new RegExp(`^${BASE}/teams/([^/]+)/decks/([^/]+)/thread/messages$`),
    handler: ({ params, body }) =>
      teamsDemo.postTeamDeckThreadMessage(
        params[0],
        decodeURIComponent(params[1]),
        (body as { body: string }).body,
      ),
  },
]

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input
  if (input instanceof URL) return input.toString()
  return input.url
}

async function handleDemoRequest(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const url = new URL(requestUrl(input))
  const method = (init?.method ?? 'GET').toUpperCase()
  const body =
    typeof init?.body === 'string' && init.body.length > 0
      ? (JSON.parse(init.body) as unknown)
      : undefined

  for (const route of routes) {
    if (route.method !== method) continue
    const match = route.pattern.exec(url.pathname)
    if (!match) continue

    const result = await route.handler({
      params: match.slice(1),
      searchParams: url.searchParams,
      body,
    })

    if (route.isBlob) {
      return new Response(result as Blob, { status: 200 })
    }
    if (result === undefined) {
      return new Response(null, { status: 204 })
    }
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  // Unmatched request: never fall back to the real `fetch` — surfacing a
  // loud error here is what makes "zero calls to barrins_api" structural
  // rather than best-effort, even for an endpoint this router forgot.
  throw new Error(`[demo mode] no fixture route for ${method} ${url.pathname}`)
}

let savedOriginalFetch: typeof fetch | null = null

/**
 * Installs the demo fetch router as `window.fetch` and returns a cleanup
 * function that restores the original `fetch`. Call the cleanup on unmount
 * so leaving `/demo` returns the app to its normal networked behavior.
 *
 * Idempotent: calling it again while already installed (e.g. React Strict
 * Mode double-invoking a mount) is a no-op rather than saving its own
 * already-intercepted `fetch` as the "original" to restore later.
 */
export function installDemoFetch(): () => void {
  if (savedOriginalFetch === null) {
    savedOriginalFetch = window.fetch
    window.fetch = ((input: RequestInfo | URL, init?: RequestInit) =>
      handleDemoRequest(input, init)) as typeof fetch
  }
  return () => {
    if (savedOriginalFetch !== null) {
      window.fetch = savedOriginalFetch
      savedOriginalFetch = null
    }
  }
}
