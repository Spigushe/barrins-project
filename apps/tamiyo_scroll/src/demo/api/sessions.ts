import type {
  Session,
  SessionComparison,
  SessionCreate,
  SessionPatch,
} from '@/schemas/tamiyoScroll'
import type { ListSessionsOptions } from '@/api/sessions'
import { DEMO_CURRENT_USER_ID, getStore, nextId, nowIso } from '../demoStore'
import { computeArchetypeSummary, computeMatchupSummary, tallyGames } from './statsCore'

/** Mirrors `src/api/sessions.ts` — see `../api/types.ts` for the compile-time proof. */

export function listSessions(
  personalDeckId: string,
  includeArchived = false,
  options: ListSessionsOptions = {},
): Promise<Session[]> {
  const store = getStore()
  let sessions = store.sessions.filter(
    (session) =>
      session.personal_deck_id === personalDeckId &&
      (includeArchived || session.archived_at === null),
  )

  if (options.search) {
    const needle = options.search.toLowerCase()
    sessions = sessions.filter((session) => session.name.toLowerCase().includes(needle))
  }

  if (options.sortBy) {
    const sortBy = options.sortBy
    const dir = options.sortDir === 'desc' ? -1 : 1
    sessions = [...sessions].sort((a, b) => {
      const key = sortBy === 'status' ? 'closed_at' : sortBy
      const av = a[key] ?? ''
      const bv = b[key] ?? ''
      return av < bv ? -dir : av > bv ? dir : 0
    })
  } else {
    sessions = [...sessions].sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
  }

  if (options.limit !== undefined) {
    const offset = options.offset ?? 0
    sessions = sessions.slice(offset, offset + options.limit)
  } else if (options.offset) {
    sessions = sessions.slice(options.offset)
  }

  return Promise.resolve(structuredClone(sessions))
}

export function createSession(payload: SessionCreate): Promise<Session> {
  const store = getStore()
  const session: Session = {
    id: nextId(),
    owner_id: DEMO_CURRENT_USER_ID,
    personal_deck_id: payload.personal_deck_id,
    name: payload.name,
    type: payload.type,
    notes: payload.notes ?? null,
    location: payload.location ?? null,
    created_at: nowIso(),
    started_at: nowIso(),
    ended_at: null,
    closed_at: null,
    archived_at: null,
    hue: null,
  }
  store.sessions.push(session)
  return Promise.resolve(structuredClone(session))
}

export function updateSession(
  sessionId: string,
  payload: SessionPatch,
): Promise<Session> {
  const store = getStore()
  const session = store.sessions.find((candidate) => candidate.id === sessionId)
  if (!session) throw new Error(`Demo session not found: ${sessionId}`)
  if (payload.name !== undefined) session.name = payload.name
  if (payload.notes !== undefined) session.notes = payload.notes
  if (payload.location !== undefined) session.location = payload.location ?? null
  if (payload.started_at !== undefined) session.started_at = payload.started_at
  if (payload.ended_at !== undefined) session.ended_at = payload.ended_at
  if (payload.hue !== undefined) session.hue = payload.hue
  if (payload.close) session.closed_at = nowIso()
  if (payload.reopen) session.closed_at = null
  if (payload.restore) session.archived_at = null
  return Promise.resolve(structuredClone(session))
}

export function archiveSession(sessionId: string): Promise<void> {
  const store = getStore()
  const session = store.sessions.find((candidate) => candidate.id === sessionId)
  if (session) session.archived_at = nowIso()
  return Promise.resolve()
}

/** Session vs. baseline comparison — mirrors `_compute_session_stats`:
 * "session" = matches explicitly logged into it, "baseline" = the same
 * deck's earlier matches (`created_at < session.created_at`), regardless of
 * which (if any) other session they belong to. */
export function getSessionComparison(sessionId: string): Promise<SessionComparison> {
  const store = getStore()
  const session = store.sessions.find((candidate) => candidate.id === sessionId)
  if (!session) throw new Error(`Demo session not found: ${sessionId}`)

  const activeMetaDecks = store.metaDecks.filter((deck) => deck.archived_at === null)
  const activeDeckIds = new Set(activeMetaDecks.map((deck) => deck.id))
  const metaDecksById = new Map(activeMetaDecks.map((deck) => [deck.id, deck]))

  const sessionMatches = store.matches.filter(
    (match) =>
      match.session_id === session.id && activeDeckIds.has(match.opponent_deck_id),
  )
  const baselineMatches = store.matches.filter(
    (match) =>
      match.personal_deck_id === session.personal_deck_id &&
      match.created_at < session.created_at &&
      activeDeckIds.has(match.opponent_deck_id),
  )

  const sessionTally = tallyGames(sessionMatches)
  const baselineTally = tallyGames(baselineMatches)

  const comparison: SessionComparison = {
    session: structuredClone(session),
    session_match_count: sessionMatches.length,
    baseline_match_count: baselineMatches.length,
    session_wins: sessionTally.wins,
    session_losses: sessionTally.losses,
    baseline_wins: baselineTally.wins,
    baseline_losses: baselineTally.losses,
    session_archetype_summary: computeArchetypeSummary(activeMetaDecks, sessionMatches),
    baseline_archetype_summary: computeArchetypeSummary(activeMetaDecks, baselineMatches),
    session_matchup_summary: computeMatchupSummary(sessionMatches, metaDecksById),
    baseline_matchup_summary: computeMatchupSummary(baselineMatches, metaDecksById),
  }
  return Promise.resolve(comparison)
}

/** Placeholder PDF blob — no WeasyPrint call, no network, just enough for the "Download report" button to work. */
export function getSessionReportPdf(_sessionId: string): Promise<Blob> {
  return Promise.resolve(
    new Blob(['Demo mode — no real report is generated.'], { type: 'application/pdf' }),
  )
}
