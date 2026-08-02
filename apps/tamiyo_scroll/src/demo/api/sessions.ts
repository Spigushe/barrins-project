import type { Session } from '@/schemas/tamiyoScroll'
import { getStore } from '../demoStore'

/**
 * `MatchJournalSection` (part of `SuiviBo3Tab`) unconditionally calls
 * `useSessions` for its session badges, so the demo fetch router needs a
 * handler for it even though Sessions isn't one of S7's three tabs. Only
 * `listSessions` is mirrored — the read path actually exercised by the three
 * tabs — not the full `src/api/sessions.ts` surface (session CRUD lives on
 * the dedicated Sessions tab, out of scope here).
 */
export function listSessions(
  personalDeckId: string,
  includeArchived = false,
): Promise<Session[]> {
  const store = getStore()
  const sessions = store.sessions.filter(
    (session) =>
      session.personal_deck_id === personalDeckId &&
      (includeArchived || session.archived_at === null),
  )
  return Promise.resolve(structuredClone(sessions))
}
